from __future__ import annotations

import asyncio

import openai
from textual import work, log, on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.events import Timer
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from elia_chat.models import Thread, ChatMessage
from elia_chat.widgets.chatbox import Chatbox
from elia_chat.widgets.conversation_header import ConversationHeader
from elia_chat.widgets.conversation_options import DEFAULT_MODEL, ConversationOptions, \
    GPTModel


# [
#     {"role": "system", "content": "You are a helpful assistant."},
#     # {"role": "user", "content": "Who won the world series in 2020?"},
#     # {"role": "assistant",
#     #  "content": "The Los Angeles Dodgers won the World Series in 2020."},
#     # {"role": "user", "content": "Where was it played?"}
# ]


# {
#  'id': 'chatcmpl-6p9XYPYSTTRi0xEviKjjilqrWU2Ve',
#  'object': 'chat.completion',
#  'created': 1677649420,
#  'model': 'gpt-3.5-turbo',
#  'usage': {'prompt_tokens': 56, 'completion_tokens': 31, 'total_tokens': 87},
#  'choices': [
#    {
#     'message': {
#       'role': 'assistant',
#       'content': 'The 2020 World Series was played in Arlington, Texas at the Globe Life Field, which was the new home stadium for the Texas Rangers.'},
#     'finish_reason': 'stop',
#     'index': 0
#    }
#   ]
# }


class Conversation(Widget):
    chosen_model: GPTModel = reactive(DEFAULT_MODEL)

    def __init__(self):
        super().__init__()

        # The thread initially only contains the system message.
        self.conversation_scroll = None
        self.thread = Thread(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant.",
                )
            ]
        )
        self._response_stream_timer: Timer | None = None

    class AgentResponseStarted(Message):
        pass

    class AgentResponseComplete(Message):
        pass

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.thread.messages) == 1  # Contains system message at first.

    def show_latest_message(self):
        if self.conversation_scroll is not None:
            self.call_after_refresh(self.conversation_scroll.scroll_end,
                                    animate=False)

    @work(exclusive=True)
    async def new_user_message(self, user_message: str) -> None:
        user_message = ChatMessage(role="user", content=user_message)
        self.thread.messages.append(user_message)
        # If the thread was empty, and now it's not, remove the ConversationOptions.
        if len(self.thread.messages) == 2:
            log.debug(
                f"First user message received in "
                f"conversation with model {self.chosen_model.name!r}"
            )
            try:
                options = self.query_one(ConversationOptions)
            except NoMatches:
                log.error("Couldn't remove ConversationOptions as it wasn't found.")
            else:
                await options.remove()

        container = self.query_one(VerticalScroll)
        await container.mount(Chatbox(user_message))

        self.show_latest_message()

        self.post_message(self.AgentResponseStarted())

        streaming_response = openai.ChatCompletion.create(
            model=self.chosen_model.name,
            messages=self.thread.messages,
            stream=True,
        )

        # TODO: We need to add the assistants response to the thread!!!
        # TODO: We need to handle RateLimitError in the worker.

        response_chatbox = Chatbox(
            message=ChatMessage(role="assistant", content=""),
            classes="assistant-message",
        )
        await container.mount(response_chatbox)

        def handle_next_event():
            try:
                event = next(streaming_response)
                choice = event["choices"][0]
                if choice.get("finish_reason") in {"stop", "length",
                                                   "content_filter"}:
                    self.post_message(self.AgentResponseComplete())
                    if self._response_stream_timer is not None:
                        self._response_stream_timer.stop()
                    return
                response_chatbox.append_chunk(event)
                self.show_latest_message()
            except (StopAsyncIteration, IndexError):
                self.post_message(self.AgentResponseComplete())
                if self._response_stream_timer is not None:
                    self._response_stream_timer.stop()

        self._response_stream_timer = self.set_interval(0.05, handle_next_event)

    @on(AgentResponseComplete)
    def stop_response_stream_timer(self) -> None:
        timer = self._response_stream_timer
        if timer is not None:
            timer.stop()

    def compose(self) -> ComposeResult:
        yield ConversationHeader(title="Untitled Chat")
        with VerticalScroll() as vertical_scroll:
            self.conversation_scroll = vertical_scroll
            vertical_scroll.can_focus = False
            yield ConversationOptions()

            # TODO - check if conversation is pre-existing.
            #  If it already exists, load it here.
            #  If it's a new empty conversation, show the options for a new conversation.
