from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from textual.widgets import Label

from elia_chat import constants
from textual import log, on, work, events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, ChatMessage
from elia_chat.screens.chat_details import ChatDetails
from elia_chat.widgets.agent_is_typing import ResponseStatus
from elia_chat.widgets.chat_header import ChatHeader, TitleStatic
from elia_chat.widgets.prompt_input import PromptInput
from elia_chat.widgets.chatbox import Chatbox
from elia_chat.widgets.tool_approval_dialog import ToolApprovalDialog


if TYPE_CHECKING:
    from elia_chat.app import Elia
    from litellm.types.completion import (
        ChatCompletionUserMessageParam,
        ChatCompletionAssistantMessageParam,
        ChatCompletionToolMessageParam,
    )


class ChatPromptInput(PromptInput):
    BINDINGS = [Binding("escape", "app.pop_screen", "Close chat", key_display="esc")]


class Chat(Widget):
    BINDINGS = [
        Binding("ctrl+r", "rename", "Rename", key_display="^r"),
        Binding("shift+down", "scroll_container_down", show=False),
        Binding("shift+up", "scroll_container_up", show=False),
        Binding(
            key="g",
            action="focus_first_message",
            description="First message",
            key_display="g",
            show=False,
        ),
        Binding(
            key="G",
            action="focus_latest_message",
            description="Latest message",
            show=False,
        ),
        Binding(key="f2", action="details", description="Chat info"),
    ]

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self, chat_data: ChatData) -> None:
        super().__init__()
        self.chat_data = chat_data
        self.elia = cast("Elia", self.app)
        self.model = chat_data.model

    @dataclass
    class AgentResponseStarted(Message):
        pass

    @dataclass
    class AgentResponseComplete(Message):
        chat_id: int | None
        message: ChatMessage
        chatbox: Chatbox

    @dataclass
    class AgentResponseFailed(Message):
        """Sent when the agent fails to respond e.g. cant connect.
        Can be used to reset UI state."""

        last_message: ChatMessage

    @dataclass
    class NewUserMessage(Message):
        content: str

    def compose(self) -> ComposeResult:
        yield ResponseStatus()
        yield ChatHeader(chat=self.chat_data, model=self.model)

        with VerticalScroll(id="chat-container") as vertical_scroll:
            vertical_scroll.can_focus = False

        yield ChatPromptInput(id="prompt")

    async def on_mount(self, _: events.Mount) -> None:
        """
        When the component is mounted, we need to check if there is a new chat to start
        """
        await self.load_chat(self.chat_data)

    @property
    def chat_container(self) -> VerticalScroll:
        return self.query_one("#chat-container", VerticalScroll)

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.chat_data.messages) == 1  # Contains system message at first.

    def scroll_to_latest_message(self):
        container = self.chat_container
        container.refresh()
        container.scroll_end(animate=False, force=True)

    @on(AgentResponseFailed)
    def restore_state_on_agent_failure(self, event: Chat.AgentResponseFailed) -> None:
        original_prompt = event.last_message.message.get("content", "")
        if isinstance(original_prompt, str):
            self.query_one(ChatPromptInput).text = original_prompt

    async def new_user_message(self, content: str) -> None:
        log.debug(f"User message submitted in chat {self.chat_data.id!r}: {content!r}")

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        user_message: ChatCompletionUserMessageParam = {
            "content": content,
            "role": "user",
        }

        user_chat_message = ChatMessage(user_message, now_utc, self.chat_data.model)
        self.chat_data.messages.append(user_chat_message)
        user_message_chatbox = Chatbox(user_chat_message, self.chat_data.model)

        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(user_message_chatbox)

        self.scroll_to_latest_message()
        self.post_message(self.NewUserMessage(content))

        await ChatsManager.add_message_to_chat(
            chat_id=self.chat_data.id, message=user_chat_message
        )

        prompt = self.query_one(ChatPromptInput)
        prompt.submit_ready = False
        self.stream_agent_response()

    @work(thread=True, group="agent_response")
    async def stream_agent_response(self) -> None:
        model = self.chat_data.model
        log.debug(f"Creating streaming response with model {model.name!r}")

        import litellm
        from litellm import ModelResponse, acompletion
        from litellm.utils import trim_messages

        raw_messages = [message.message for message in self.chat_data.messages]

        messages: list[ChatCompletionUserMessageParam] = trim_messages(
            raw_messages, model.name
        )  # type: ignore

        # Get available MCP tools
        mcp_tools = []
        try:
            mcp_tools = await self.elia.mcp_manager.get_available_tools()
            log.debug(f"Found {len(mcp_tools)} MCP tools available")
        except Exception as e:
            log.warning(f"Failed to get MCP tools: {e}")

        litellm.organization = model.organization
        try:
            # Include tools in the completion request if available
            completion_kwargs = {
                "messages": messages,
                "stream": True,
                "model": model.name,
                "temperature": model.temperature,
                "max_retries": model.max_retries,
                "api_key": model.api_key.get_secret_value() if model.api_key else None,
                "api_base": model.api_base.unicode_string() if model.api_base else None,
            }
            
            if mcp_tools:
                completion_kwargs["tools"] = mcp_tools
                completion_kwargs["tool_choice"] = "auto"
            
            response = await acompletion(**completion_kwargs)
        except Exception as exception:
            self.app.notify(
                f"{exception}",
                title="Error",
                severity="error",
                timeout=constants.ERROR_NOTIFY_TIMEOUT_SECS,
            )
            self.post_message(self.AgentResponseFailed(self.chat_data.messages[-1]))
            return

        ai_message: ChatCompletionAssistantMessageParam = {
            "content": "",
            "role": "assistant",
        }
        now = datetime.datetime.now(datetime.timezone.utc)

        message = ChatMessage(message=ai_message, model=model, timestamp=now)
        response_chatbox = Chatbox(
            message=message,
            model=self.chat_data.model,
            classes="response-in-progress",
        )
        self.post_message(self.AgentResponseStarted())
        self.app.call_from_thread(self.chat_container.mount, response_chatbox)

        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        try:
            chunk_count = 0
            tool_calls = []
            
            async for chunk in response:
                chunk = cast(ModelResponse, chunk)
                response_chatbox.border_title = "Agent is responding..."

                choice = chunk.choices[0]
                delta = choice.delta
                
                # Handle content chunks
                chunk_content = delta.content
                if isinstance(chunk_content, str):
                    self.app.call_from_thread(
                        response_chatbox.append_chunk, chunk_content
                    )
                
                # Handle tool call chunks
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        # Ensure we have enough tool_calls in our list
                        while len(tool_calls) <= tool_call_delta.index:
                            tool_calls.append({
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            })
                        
                        # Update the tool call at the specified index
                        if tool_call_delta.id:
                            tool_calls[tool_call_delta.index]["id"] = tool_call_delta.id
                        
                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                tool_calls[tool_call_delta.index]["function"]["name"] = tool_call_delta.function.name
                            if tool_call_delta.function.arguments:
                                tool_calls[tool_call_delta.index]["function"]["arguments"] += tool_call_delta.function.arguments

                scroll_y = self.chat_container.scroll_y
                max_scroll_y = self.chat_container.max_scroll_y
                if scroll_y in range(max_scroll_y - 3, max_scroll_y + 1):
                    self.app.call_from_thread(
                        self.chat_container.scroll_end, animate=False
                    )

                chunk_count += 1
            
            # If we have tool calls, handle them
            if tool_calls:
                # Parse arguments for each tool call
                for tool_call in tool_calls:
                    try:
                        import json
                        tool_call["function"]["arguments"] = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError as e:
                        log.error(f"Failed to parse tool call arguments: {e}")
                        tool_call["function"]["arguments"] = {}
                
                # Add tool calls to the assistant message
                response_chatbox.message.message["tool_calls"] = tool_calls
                
                # Handle tool calls and continue conversation
                await self._handle_tool_calls_and_continue(tool_calls, response_chatbox)
            else:
                # No tool calls, complete the response normally
                self.post_message(
                    self.AgentResponseComplete(
                        chat_id=self.chat_data.id,
                        message=response_chatbox.message,
                        chatbox=response_chatbox,
                    )
                )
                
        except Exception as e:
            log.error(f"Error in stream_agent_response: {e}")
            self.notify(
                "There was a problem using this model. "
                "Please check your configuration file.",
                title="Error",
                severity="error",
                timeout=constants.ERROR_NOTIFY_TIMEOUT_SECS,
            )
            self.post_message(self.AgentResponseFailed(self.chat_data.messages[-1]))

    @on(AgentResponseFailed)
    @on(AgentResponseStarted)
    async def agent_started_responding(
        self, event: AgentResponseFailed | AgentResponseStarted
    ) -> None:
        try:
            awaiting_reply = self.chat_container.query_one("#awaiting-reply", Label)
        except NoMatches:
            pass
        else:
            if awaiting_reply:
                await awaiting_reply.remove()

    @on(AgentResponseComplete)
    def agent_finished_responding(self, event: AgentResponseComplete) -> None:
        # Ensure the thread is updated with the message from the agent
        self.chat_data.messages.append(event.message)
        event.chatbox.border_title = "Agent"
        event.chatbox.remove_class("response-in-progress")
        prompt = self.query_one(ChatPromptInput)
        prompt.submit_ready = True

    @on(PromptInput.PromptSubmitted)
    async def user_chat_message_submitted(
        self, event: PromptInput.PromptSubmitted
    ) -> None:
        if self.allow_input_submit is True:
            user_message = event.text
            await self.new_user_message(user_message)

    @on(PromptInput.CursorEscapingTop)
    async def on_cursor_up_from_prompt(
        self, event: PromptInput.CursorEscapingTop
    ) -> None:
        self.focus_latest_message()

    @on(Chatbox.CursorEscapingBottom)
    def move_focus_to_prompt(self) -> None:
        self.query_one(ChatPromptInput).focus()

    @on(TitleStatic.ChatRenamed)
    async def handle_chat_rename(self, event: TitleStatic.ChatRenamed) -> None:
        if event.chat_id == self.chat_data.id and event.new_title:
            self.chat_data.title = event.new_title
            header = self.query_one(ChatHeader)
            header.update_header(self.chat_data, self.model)
            await ChatsManager.rename_chat(event.chat_id, event.new_title)

    def get_latest_chatbox(self) -> Chatbox:
        return self.query(Chatbox).last()

    def focus_latest_message(self) -> None:
        try:
            self.get_latest_chatbox().focus()
        except NoMatches:
            pass

    def action_rename(self) -> None:
        title_static = self.query_one(TitleStatic)
        title_static.begin_rename()

    def action_focus_latest_message(self) -> None:
        self.focus_latest_message()

    def action_focus_first_message(self) -> None:
        try:
            self.query(Chatbox).first().focus()
        except NoMatches:
            pass

    def action_scroll_container_up(self) -> None:
        if self.chat_container:
            self.chat_container.scroll_up()

    def action_scroll_container_down(self) -> None:
        if self.chat_container:
            self.chat_container.scroll_down()

    async def action_details(self) -> None:
        await self.app.push_screen(ChatDetails(self.chat_data))

    async def _handle_tool_calls_and_continue(self, tool_calls: list, response_chatbox: Chatbox) -> None:
        """Handle tool calls and continue the conversation with results."""
        try:
            # Process tool calls from the main thread
            self.app.call_from_thread(self._process_tool_calls, tool_calls, response_chatbox)
            
        except Exception as e:
            log.error(f"Error handling tool calls: {e}")
            self.post_message(
                self.AgentResponseComplete(
                    chat_id=self.chat_data.id,
                    message=response_chatbox.message,
                    chatbox=response_chatbox,
                )
            )

    @work(thread=False, group="tool_execution")
    async def _process_tool_calls(self, tool_calls: list, response_chatbox: Chatbox) -> None:
        """Process tool calls from the main thread."""
        try:
            # Check for tool approval and execute tools
            tool_results = []
            
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]
                call_id = tool_call["id"]
                
                # Check if tool needs approval
                is_auto_approved = await self.elia.mcp_manager.is_tool_auto_approved(tool_name)
                
                if not is_auto_approved:
                    # Show tool approval dialog
                    approved = await self._show_tool_approval_dialog(tool_name, arguments)
                    if not approved:
                        # User denied tool execution
                        tool_results.append({
                            "tool_call_id": call_id,
                            "role": "tool",
                            "name": tool_name,
                            "content": "Tool execution was denied by user."
                        })
                        continue
                
                # Show tool execution status
                response_chatbox.append_chunk(f"\n\n[Executing tool: {tool_name}...]")
                
                # Execute the tool
                try:
                    result = await self.elia.mcp_manager.execute_tool(tool_name, arguments)
                    tool_results.append({
                        "tool_call_id": call_id,
                        "role": "tool", 
                        "name": tool_name,
                        "content": result.get("content", "")
                    })
                    
                    # Show tool execution result in UI
                    response_chatbox.append_chunk(f"\n[Tool result: {result.get('content', '')[:100]}{'...' if len(result.get('content', '')) > 100 else ''}]")
                    
                except Exception as e:
                    log.error(f"Tool execution failed for {tool_name}: {e}")
                    tool_results.append({
                        "tool_call_id": call_id,
                        "role": "tool",
                        "name": tool_name, 
                        "content": f"Error: {str(e)}"
                    })
                    
                    # Show error in UI
                    response_chatbox.append_chunk(f"\n[Tool error: {str(e)}]")
            
            # Add tool result messages to conversation
            now = datetime.datetime.now(datetime.timezone.utc)
            for tool_result in tool_results:
                tool_message: "ChatCompletionToolMessageParam" = {
                    "role": "tool",
                    "content": tool_result["content"],
                    "tool_call_id": tool_result["tool_call_id"]
                }
                
                tool_chat_message = ChatMessage(
                    message=tool_message,
                    timestamp=now,
                    model=self.chat_data.model
                )
                self.chat_data.messages.append(tool_chat_message)
            
            # Complete the current assistant response
            self.post_message(
                self.AgentResponseComplete(
                    chat_id=self.chat_data.id,
                    message=response_chatbox.message,
                    chatbox=response_chatbox,
                )
            )
            
            # Continue conversation with tool results if we have any
            if tool_results:
                # Start a new response to process tool results
                self.stream_agent_response()
            
        except Exception as e:
            log.error(f"Error processing tool calls: {e}")
            response_chatbox.append_chunk(f"\n[Error processing tools: {str(e)}]")
            self.post_message(
                self.AgentResponseComplete(
                    chat_id=self.chat_data.id,
                    message=response_chatbox.message,
                    chatbox=response_chatbox,
                )
            )

    async def _show_tool_approval_dialog(self, tool_name: str, arguments: dict) -> bool:
        """Show tool approval dialog to user.
        
        Args:
            tool_name: Name of the tool to approve
            arguments: Tool arguments
            
        Returns:
            True if user approves, False otherwise
        """
        try:
            # Get server name for the tool
            server_name = self.elia.mcp_manager.get_tool_server(tool_name)
            
            # Show modal approval dialog
            dialog = ToolApprovalDialog(tool_name, arguments, server_name)
            result = await self.app.push_screen_wait(dialog)
            
            log.info(f"Tool '{tool_name}' approval result: {result}")
            return result
            
        except Exception as e:
            log.error(f"Error showing tool approval dialog: {e}")
            # Default to deny on error
            return False

    async def load_chat(self, chat_data: ChatData) -> None:
        chatboxes = [
            Chatbox(chat_message, chat_data.model)
            for chat_message in chat_data.non_system_messages
        ]
        await self.chat_container.mount_all(chatboxes)
        self.chat_container.scroll_end(animate=False, force=True)
        chat_header = self.query_one(ChatHeader)
        chat_header.update_header(
            chat=chat_data,
            model=chat_data.model,
        )

        # If the last message didn't receive a response, try again.
        messages = chat_data.messages
        if messages and messages[-1].message["role"] == "user":
            prompt = self.query_one(ChatPromptInput)
            prompt.submit_ready = False
            self.stream_agent_response()

    def action_close(self) -> None:
        self.app.clear_notifications()
        self.app.pop_screen()
