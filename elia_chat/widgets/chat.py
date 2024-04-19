from __future__ import annotations

import os
import time
from dataclasses import dataclass

from langchain.chat_models.base import BaseChatModel
from langchain.llms.base import LLM
from langchain.schema import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.schema.messages import BaseMessageChunk
from textual import log, on, work, events
from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, EliaContext
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.chat_options import (
    GPTModel,
    get_model_by_name,
)
from elia_chat.widgets.chatbox import Chatbox


class Chat(Widget):
    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self, chat_data: ChatData) -> None:
        super().__init__()
        self.chat_data = chat_data
        self.persona_directive = os.getenv(
            "ELIA_DIRECTIVE", "You are a helpful assistant."
        )
        # The thread initially only contains the system message.
        self.chat_container: ScrollableContainer | None = None

    @dataclass
    class AgentResponseStarted(Message):
        pass

    @dataclass
    class AgentResponseComplete(Message):
        chat_id: str | None
        message: BaseMessage

    @dataclass
    class FirstMessageSent(Message):
        chat_data: ChatData

    @dataclass
    class UserMessageSubmitted(Message):
        chat_id: str
        message: BaseMessage

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.chat_data.messages) == 1  # Contains system message at first.

    def scroll_to_latest_message(self):
        if self.chat_container is not None:
            self.chat_container.refresh()
            self.chat_container.scroll_end(animate=False)

    async def new_user_message(self, content: str) -> None:
        log.debug(f"User message submitted in chat {self.chat_data.id!r}: {content!r}")
        user_message = HumanMessage(
            content=content,
            additional_kwargs={
                "timestamp": time.time(),
                "status": None,
                "end_turn": None,
                "weight": None,
                "metadata": None,
                "recipient": None,
            },
        )
        is_first_message = self.is_empty
        if is_first_message:
            log.debug(
                f"First user message received in "
                f"conversation with model {self.chat_data.model_name!r}"
            )

            # At this point, we should create the conversation in the database.
            # Note that we don't need to add the message here, since `create_chat`
            # already adds any of the messages already present in the chat.
            self.chat_data.id = str(ChatsManager.create_chat(chat_data=self.chat_data))

            # Add the first message to the thread AFTER creating the chat, since
            # we don't want ChatsManager.create_chat to persist the message for us.
            # The message will be persisted by us below, outwith this if block.

        self.chat_data.messages.append(user_message)
        if is_first_message:
            self.post_message(
                Chat.FirstMessageSent(
                    chat_data=self.chat_data,
                )
            )

        ChatsManager.add_message_to_chat(
            chat_id=str(self.chat_data.id), message=user_message
        )

        assert self.chat_data.id is not None
        self.post_message(
            Chat.UserMessageSubmitted(
                chat_id=str(self.chat_data.id), message=user_message
            )
        )

        assert self.chat_data.model_name is not None
        user_message_chatbox = Chatbox(user_message, self.chat_data.model_name)

        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."

        await self.chat_container.mount(user_message_chatbox)
        self.scroll_to_latest_message()
        self.post_message(self.AgentResponseStarted())
        self.stream_agent_response()

    async def clear_thread(self) -> None:
        """Remove the internal thread representing the chat, and update the DOM."""

        # We have to maintain the system message.
        self.chat_data.messages = self.chat_data.messages[:1]

        assert self.chat_container is not None

        # Clear the part of the DOM containing the chat messages.
        # Important that we make a copy before removing inside the loop!
        children = list(self.chat_container.children)
        for child in children:
            await child.remove()

    @work(exclusive=True)
    async def stream_agent_response(self) -> None:
        self.scroll_to_latest_message()
        log.debug(
            f"Creating streaming response with model {self.chat_data.model_name!r}"
        )
        selected_model: GPTModel = get_model_by_name(self.chat_data.model_name)
        llm: BaseChatModel = selected_model.model
        trimmed_messages = self.trim_messages(
            model=llm,
            messages=self.chat_data.messages,
            max_tokens=selected_model.token_limit,
            preserve_system_message=True,
        )
        streaming_response = llm.astream(input=trimmed_messages)
        # TODO - ensure any metadata available in streaming response is passed through
        message = AIMessage(
            content="",
            additional_kwargs={
                "timestamp": time.time(),
                "status": None,
                "end_turn": None,
                "weight": None,
                "metadata": None,
                "recipient": None,
            },
        )
        assert self.chat_data.model_name is not None
        response_chatbox = Chatbox(
            message=message,
            model_name=self.chat_data.model_name,
        )
        assert (
            self.chat_container is not None
        ), "Textual has mounted container at this point in the lifecycle."
        await self.chat_container.mount(response_chatbox)
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
            )
        )

    @on(AgentResponseComplete)
    def agent_finished_responding(self, event: AgentResponseComplete) -> None:
        # Ensure the thread is updated with the message from the agent
        self.chat_data.messages.append(event.message)

    @on(Input.Submitted, "#chat-input")
    async def user_chat_message_submitted(self, event: Input.Submitted) -> None:
        if self.allow_input_submit is True:
            user_message = event.value
            event.input.value = ""
            await self.new_user_message(user_message)

    # async def load_chat(self, chat: ChatData | None) -> None:
    #     assert self.chat_container is not None
    #     if chat is not None:
    #         self.chat_data = chat
    #     else:
    #         self.chat_data = ChatData(
    #             id=None,
    #             title=None,
    #             create_timestamp=None,
    #             model_name=self.model_name,
    #             messages=[
    #                 SystemMessage(
    #                     content=self.persona_directive,
    #                     additional_kwargs={
    #                         "timestamp": time.time(),
    #                         "status": None,
    #                         "end_turn": None,
    #                         "weight": None,
    #                         "metadata": None,
    #                         "recipient": "all",
    #                     },
    #                 )
    #             ],
    #         )

    #     chat_data = self.chat_data
    #     chatboxes = [
    #         Chatbox(chat_message, self.chat_data.model_name)
    #         for chat_message in self.chat_data.non_system_messages
    #     ]
    #     await self.chat_container.mount_all(chatboxes)
    #     self.chat_container.scroll_end(animate=False)

    #     chat_header = self.query_one(ChatHeader)
    #     chat_header.title = chat_data.short_preview or "Untitled Chat"
    #     chat_header.model_name = chat_data.model_name or "unknown model"

    def compose(self) -> ComposeResult:
        yield ChatHeader()
        with Vertical(id="chat-input-container"):
            yield Input(placeholder="[I] Enter your message here...", id="chat-input")
            yield AgentIsTyping()

        with VerticalScroll() as vertical_scroll:
            self.chat_container = vertical_scroll
            vertical_scroll.can_focus = False

    async def on_mount(self, _: events.Mount) -> None:
        """
        When the component is mounted, we need to check if there is a new chat to start
        """
        app_context: EliaContext = self.app.elia_context  # type: ignore[attr-defined]
        gpt_model = app_context.gpt_model
        self.chat_data.model_name = gpt_model.name
        chat_input = self.query_one("#chat-input")
        if app_context.chat_message is not None:
            await self.new_user_message(app_context.chat_message)
            chat_input.focus()

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
