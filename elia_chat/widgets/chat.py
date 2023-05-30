from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import openai
from textual import work, log, on
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical, ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input

from elia_chat.chats_manager import ChatsManager
from elia_chat.models import ChatData, ChatMessage
from elia_chat.widgets.agent_is_typing import AgentIsTyping
from elia_chat.widgets.chatbox import Chatbox
from elia_chat.widgets.chat_header import ChatHeader
from elia_chat.widgets.chat_options import (
    DEFAULT_MODEL,
    ChatOptions,
)


class Chat(Widget):
    allow_input_submit = reactive(True)
    """Used to lock the chat input while the agent is responding."""

    def __init__(self) -> None:
        super().__init__()

        # The thread initially only contains the system message.
        self.chat_container: ScrollableContainer | None = None
        self.chat_options: ChatOptions | None = None
        self.chat_data = ChatData(
            id=None,
            title=None,
            create_timestamp=None,
            model_name=DEFAULT_MODEL.name,
            messages=[
                ChatMessage(
                    id=None,
                    role="system",
                    content="You are a helpful assistant.",
                    timestamp=time.time(),
                    status=None,
                    end_turn=None,
                    weight=None,
                    metadata={},
                    recipient="all",
                )
            ],
        )

    @dataclass
    class AgentResponseStarted(Message):
        pass

    @dataclass
    class AgentResponseComplete(Message):
        chat_id: str | None
        message: ChatMessage

    @dataclass
    class FirstMessageSent(Message):
        chat_data: ChatData

    @dataclass
    class SavedChatLoaded(Message):
        chat_data: ChatData

    @dataclass
    class UserMessageSubmitted(Message):
        chat_id: str
        message: ChatMessage

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
        user_message = ChatMessage(
            id=None,
            role="user",
            content=content,
            timestamp=time.time(),
            status=None,
            end_turn=None,
            weight=None,
            metadata=None,
            recipient=None,
        )
        # If the thread was empty, and now it's not, remove the ConversationOptions.
        is_first_message = self.is_empty
        if is_first_message:
            log.debug(
                f"First user message received in "
                f"conversation with model {self.chat_data.model_name!r}"
            )
            assert self.chat_options is not None
            self.chat_options.display = False

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

    @property
    def outgoing_messages(self) -> list[dict[str, Any]]:
        return [
            {"role": message.get("role"), "content": message.get("content")}
            for message in self.chat_data.messages
        ]

    @work(exclusive=True)
    async def stream_agent_response(self) -> None:
        self.scroll_to_latest_message()
        log.debug(
            f"Creating streaming response with model {self.chat_data.model_name!r}"
        )
        streaming_response = await openai.ChatCompletion.acreate(
            model=self.chat_data.model_name,
            messages=self.outgoing_messages,
            stream=True,
        )

        # TODO - ensure any metadata available in streaming response is passed through
        message = ChatMessage(
            id=None,
            role="assistant",
            content="",
            timestamp=time.time(),
            status=None,
            end_turn=None,
            weight=None,
            metadata=None,
            recipient=None,
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

        while True:
            # TODO: We need to handle RateLimitError in the worker.
            try:
                event = await streaming_response.__anext__()
                choice = event["choices"][0]
            except (StopAsyncIteration, StopIteration, IndexError):
                self.post_message(
                    self.AgentResponseComplete(
                        chat_id=self.chat_data.id,
                        message=message,
                    ),
                )
            else:
                finish_reason = choice.get("finish_reason")
                if finish_reason in {"stop", "length", "content_filter"}:
                    log.debug(
                        f"Agent response finished. Finish reason is {finish_reason!r}."
                    )
                    response_message = response_chatbox.message
                    self.post_message(
                        self.AgentResponseComplete(
                            chat_id=self.chat_data.id,
                            message=response_message,
                        )
                    )
                    return
                response_chatbox.append_chunk(event)
                scroll_y = self.chat_container.scroll_y
                max_scroll_y = self.chat_container.max_scroll_y
                if scroll_y in range(max_scroll_y - 3, max_scroll_y + 1):
                    self.chat_container.scroll_end(animate=False)
            await asyncio.sleep(0.01)

    @on(AgentResponseComplete)
    def agent_finished_responding(self, event: AgentResponseComplete) -> None:
        # Ensure the thread is updated with the message from the agent
        self.chat_data.messages.append(event.message)

    @on(Input.Submitted, "#chat-input")
    async def user_chat_message_submitted(self, event: Input.Submitted) -> None:
        if self.allow_input_submit:
            user_message = event.value
            event.input.value = ""
            await self.new_user_message(user_message)

    async def load_chat(self, chat: ChatData) -> None:
        assert self.chat_options is not None
        assert self.chat_container is not None

        # If the options display is visible, get rid of it.
        self.chat_options.display = False

        # Update the chat data
        await self.clear_thread()
        self.chat_data = chat

        assert self.chat_data.model_name is not None
        chatboxes = [
            Chatbox(chat_message, self.chat_data.model_name)
            for chat_message in chat.non_system_messages
        ]
        await self.chat_container.mount_all(chatboxes)
        self.chat_container.scroll_end(animate=False)

        chat_header = self.query_one(ChatHeader)
        chat_header.title = chat.short_preview or "Untitled Chat"
        chat_header.model_name = chat.model_name or "unknown model"
        self.post_message(Chat.SavedChatLoaded(chat))  # TODO - required?

    async def prepare_for_new_chat(self) -> None:
        await self.clear_thread()

        # Show the options to let the user configure the new chat.
        assert self.chat_options is not None

        chat_header = self.query_one(ChatHeader)
        self.chat_data.id = None
        chat_header.title = "Untitled Chat"
        chat_header.model_name = self.chat_data.model_name or "unknown model"
        self.chat_options.display = True

        log.debug(f"Prepared for new chat. Chat data = {self.chat_data}")

    def compose(self) -> ComposeResult:
        yield ChatHeader()
        with Vertical(id="chat-input-container"):
            yield Input(placeholder="[I] Enter your message here...", id="chat-input")
            yield AgentIsTyping()

        with VerticalScroll() as vertical_scroll:
            self.chat_container = vertical_scroll
            vertical_scroll.can_focus = False

        self.chat_options = ChatOptions()
        yield self.chat_options

        # TODO - check if conversation is pre-existing.
        #  If it already exists, load it here.
        #  If it's a new empty conversation, show the
        #  options for a new conversation.
