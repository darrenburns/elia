from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models import LLM
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    BaseMessageChunk,
)
from textual import log, on, work, events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData
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
    BINDINGS = [Binding("escape", "pop_screen", "Home", key_display="esc")]

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
        chat_id: str | None
        message: BaseMessage
        chatbox: Chatbox

    @dataclass
    class FirstMessageSent(Message):
        chat_data: ChatData

    @dataclass
    class UserMessageSubmitted(Message):
        chat_id: str
        message: BaseMessage

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
        user_message = HumanMessage(
            content=content,
            additional_kwargs={
                "timestamp": datetime.datetime.now(datetime.UTC),
            },
        )
        self.chat_data.messages.append(user_message)
        await ChatsManager.add_message_to_chat(
            chat_id=str(self.chat_data.id), message=user_message
        )

        self.post_message(
            Chat.UserMessageSubmitted(
                chat_id=str(self.chat_data.id), message=user_message
            )
        )
        user_message_chatbox = Chatbox(user_message, self.chat_data.model_name)

        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(user_message_chatbox)
        self.scroll_to_latest_message()
        self.post_message(self.AgentResponseStarted())
        self.stream_agent_response()

    @work(exclusive=True)
    async def stream_agent_response(self) -> None:
        # TODO - lock the prompt input box here?

        self.scroll_to_latest_message()
        log.debug(
            f"Creating streaming response with model {self.chat_data.model_name!r}"
        )
        selected_model: EliaChatModel = get_model_by_name(
            self.chat_data.model_name, self.elia.launch_config
        )
        llm: BaseChatModel = selected_model.get_langchain_chat_model(
            self.elia.launch_config
        )
        messages = self.chat_data.messages
        if selected_model.provider != "anthropic":
            self.trim_messages(
                model=llm,
                messages=messages,
                max_tokens=selected_model.context_window,
                preserve_system_message=True,
            )
        streaming_response = llm.astream(input=messages)
        # TODO - ensure any metadata available in streaming response is passed through
        message = AIMessage(
            content="",
            additional_kwargs={
                "timestamp": datetime.datetime.now(datetime.UTC),
            },
        )
        assert self.chat_data.model_name is not None
        response_chatbox = Chatbox(
            message=message,
            model_name=self.chat_data.model_name,
            classes="response-in-progress",
        )
        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(response_chatbox)
        response_chatbox.border_title = "Agent is responding..."

        async for token in streaming_response:
            if isinstance(token, BaseMessageChunk):
                token_str = token.content
            else:
                token_str = str(token)
            response_chatbox.append_chunk(token_str)
            scroll_y = self.chat_container.scroll_y
            max_scroll_y = self.chat_container.max_scroll_y
            if scroll_y in range(max_scroll_y - 3, max_scroll_y + 1):
                self.chat_container.scroll_end(animate=False)

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

    async def load_chat(self, chat_data: ChatData) -> None:
        assert self.chat_container is not None
        chatboxes = [
            Chatbox(chat_message, self.chat_data.model_name)
            for chat_message in self.chat_data.non_system_messages
        ]
        await self.chat_container.mount_all(chatboxes)
        self.chat_container.scroll_end(animate=False, force=True)

        if chat_data.messages and chat_data.messages[-1].type == "human":
            self.post_message(self.AgentResponseStarted())
            self.stream_agent_response()

        chat_header = self.query_one(ChatHeader)
        chat_header.title = chat_data.title or chat_data.short_preview.replace(
            "\n", " "
        )
        chat_header.model_name = chat_data.model_name or "unknown model"

    @classmethod
    def get_message_length(
        cls,
        messages: list[BaseMessage],
        model: BaseChatModel | LLM,
    ) -> tuple[list[tuple[BaseMessage, int]], int]:
        """
        Get the length of messages
        """
        if len(messages) == 0:
            raise ValueError("No messages provided")
        total_length = 0
        message_lengths: list[tuple[BaseMessage, int]] = []
        for message in messages:
            message_length = model.get_num_tokens_from_messages(messages=[message])
            message_lengths.append((message, message_length))
            total_length += message_length
        return message_lengths, total_length

    @classmethod
    def trim_messages(
        cls,
        model: BaseChatModel | LLM,
        messages: list[BaseMessage],
        max_tokens: int,
        preserve_system_message: bool = True,
    ) -> list[BaseMessage]:
        """
        Trim messages to fit within max_tokens

        This method pre-calculates the length of each message, then iterates
        through the messages in reverse order, adding them to a list until
        the total number of tokens exceeds max_tokens. Optionally, the system
        message can be preserved at the beginning of the chat.

        Parameters
        ----------
        model: BaseChatModel | LLM
            Language model
        messages: list[BaseMessage]
            Messages
        max_tokens: int
            Maximum number of tokens
        preserve_system_message: bool
            Whether to preserve the system message at the beginning of the chat

        Returns
        -------
        list[BaseMessage]
            Trimmed messages
        """
        message_lengths, total_length = cls.get_message_length(
            messages=messages, model=model
        )
        if total_length <= max_tokens:
            return messages
        total_tokens = 0
        trimmed_messages: list[BaseMessage] = []
        preserved_messages: list[BaseMessage] = []
        if preserve_system_message is True and isinstance(messages[0], SystemMessage):
            system_message_tokens = model.get_num_tokens_from_messages(
                messages=[messages[0]]
            )
            if system_message_tokens > max_tokens:
                raise ValueError(
                    f"System message is too long ({system_message_tokens} tokens)"
                )
            total_tokens += system_message_tokens
            preserved_messages.append(messages[0])
            message_lengths = message_lengths[1:]
        for message, length in reversed(message_lengths):
            total_tokens += length
            if total_tokens > max_tokens:
                break
            else:
                trimmed_messages.append(message)
        if len(trimmed_messages) == 0:
            msg = (
                f"Unable to trim ({len(messages)}) messages to fit "
                f"within max_tokens ({max_tokens})"
            )
            raise ValueError(msg)
        return preserved_messages + list(reversed(trimmed_messages))
