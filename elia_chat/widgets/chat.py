from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from litellm import ModelResponse, acompletion
from litellm.types.completion import (
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

from litellm.utils import trim_messages
from textual import log, on, work, events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, ChatMessage
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.prompt_input import PromptInput
from elia_chat.models import (
    EliaChatModel,
    get_model_by_name,
)
from elia_chat.widgets.chatbox import Chatbox


if TYPE_CHECKING:
    from elia_chat.app import Elia


class Chat(Widget):
    BINDINGS = [
        Binding("escape", "pop_screen", "Close", key_display="esc"),
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
    ]

    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self, chat_data: ChatData) -> None:
        super().__init__()
        self.chat_data = chat_data
        self.chat_container: ScrollableContainer | None = None
        self.elia = cast("Elia", self.app)

    @dataclass
    class AgentResponseStarted(Message):
        pass

    @dataclass
    class AgentResponseComplete(Message):
        chat_id: int | None
        message: ChatMessage
        chatbox: Chatbox

    @dataclass
    class FirstMessageSent(Message):
        chat_data: ChatData

    @dataclass
    class UserMessageSubmitted(Message):
        chat_id: int
        message: ChatMessage

    def compose(self) -> ComposeResult:
        yield ChatHeader()

        with VerticalScroll() as vertical_scroll:
            self.chat_container = vertical_scroll
            vertical_scroll.can_focus = False

        yield PromptInput(id="prompt")
        yield AgentIsTyping()

    async def on_mount(self, _: events.Mount) -> None:
        """
        When the component is mounted, we need to check if there is a new chat to start
        """
        await self.load_chat(self.chat_data)
        self.query_one(PromptInput).focus()

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.chat_data.messages) == 1  # Contains system message at first.

    def scroll_to_latest_message(self):
        if self.chat_container is not None:
            self.chat_container.refresh()
            self.chat_container.scroll_end(animate=False, force=True)

    async def new_user_message(self, content: str) -> None:
        log.debug(f"User message submitted in chat {self.chat_data.id!r}: {content!r}")
        now_utc = datetime.datetime.now(datetime.UTC)
        user_message: ChatCompletionUserMessageParam = {
            "content": content,
            "role": "user",
        }
        user_chat_message = ChatMessage(
            user_message, now_utc, self.chat_data.model_name
        )
        self.chat_data.messages.append(user_chat_message)
        await ChatsManager.add_message_to_chat(
            chat_id=self.chat_data.id, message=user_chat_message
        )

        self.post_message(
            Chat.UserMessageSubmitted(
                chat_id=self.chat_data.id, message=user_chat_message
            )
        )
        user_message_chatbox = Chatbox(user_chat_message, self.chat_data.model_name)

        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(user_message_chatbox)
        self.scroll_to_latest_message()
        self.post_message(self.AgentResponseStarted())
        self.stream_agent_response()

    @work
    async def stream_agent_response(self) -> None:
        self.scroll_to_latest_message()
        log.debug(
            f"Creating streaming response with model {self.chat_data.model_name!r}"
        )
        model: EliaChatModel = get_model_by_name(
            self.chat_data.model_name, self.elia.launch_config
        )

        raw_messages = [message.message for message in self.chat_data.messages]
        messages: list[ChatCompletionUserMessageParam] = trim_messages(
            raw_messages, model.name
        )  # type: ignore
        response = await acompletion(
            messages=messages,
            stream=True,
            model=model.name,
            temperature=model.temperature,
            max_retries=model.max_retries,
        )
        ai_message: ChatCompletionAssistantMessageParam = {
            "content": "",
            "role": "assistant",
        }
        now = datetime.datetime.now(datetime.UTC)
        message = ChatMessage(message=ai_message, model=model.name, timestamp=now)

        assert self.chat_data.model_name is not None
        response_chatbox = Chatbox(
            message=message,
            model_name=self.chat_data.model_name,
            classes="response-in-progress",
        )
        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        try:
            chunk_count = 0
            async for chunk in response:
                if chunk_count == 0:
                    response_chatbox.border_title = "Agent is responding..."
                    await self.chat_container.mount(response_chatbox)

                chunk = cast(ModelResponse, chunk)
                chunk_content = chunk.choices[0].delta.content
                if isinstance(chunk_content, str):
                    response_chatbox.append_chunk(chunk_content)
                else:
                    break
                scroll_y = self.chat_container.scroll_y
                max_scroll_y = self.chat_container.max_scroll_y
                if scroll_y in range(max_scroll_y - 3, max_scroll_y + 1):
                    self.chat_container.scroll_end(animate=False)

                chunk_count += 1
        except Exception:
            self.notify(
                "There was a problem using this model. "
                "Please check your configuration file.",
                title="Error",
                severity="error",
                timeout=15,
            )
        else:
            self.post_message(
                self.AgentResponseComplete(
                    chat_id=self.chat_data.id,
                    message=response_chatbox.message,
                    chatbox=response_chatbox,
                )
            )

    @on(AgentResponseComplete)
    def agent_finished_responding(self, event: AgentResponseComplete) -> None:
        # Ensure the thread is updated with the message from the agent
        self.chat_data.messages.append(event.message)
        event.chatbox.border_title = "Agent"
        event.chatbox.remove_class("response-in-progress")

    @on(PromptInput.PromptSubmitted)
    async def user_chat_message_submitted(
        self, event: PromptInput.PromptSubmitted
    ) -> None:
        if self.allow_input_submit is True:
            user_message = event.text
            await self.new_user_message(user_message)

    @on(PromptInput.CursorEscapingTop)
    async def on_cursor_up_from_prompt(self) -> None:
        self.focus_latest_message()

    def focus_latest_message(self) -> None:
        try:
            self.query(Chatbox).last().focus()
        except NoMatches:
            pass

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

    async def load_chat(self, chat_data: ChatData) -> None:
        assert self.chat_container is not None
        chatboxes = [
            Chatbox(chat_message, self.chat_data.model_name)
            for chat_message in self.chat_data.non_system_messages
        ]
        await self.chat_container.mount_all(chatboxes)
        self.chat_container.scroll_end(animate=False, force=True)

        messages = chat_data.messages
        if messages and messages[-1].message["role"] == "user":
            self.post_message(self.AgentResponseStarted())
            self.stream_agent_response()

        chat_header = self.query_one(ChatHeader)
        chat_header.title = chat_data.title or chat_data.short_preview.replace(
            "\n", " "
        )
        chat_header.model_name = chat_data.model_name or "unknown model"
