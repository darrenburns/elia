from __future__ import annotations

import asyncio

import openai
from textual import work, log
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
        self.thread = Thread(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful assistant.",
                )
            ]
        )
        self._response_stream_timer: Timer | None = None

    @property
    def is_empty(self) -> bool:
        """True if the conversation is empty, False otherwise."""
        return len(self.thread.messages) == 1  # Contains system message at first.

    @work(exclusive=True)
    async def new_user_message(self, user_message: str) -> None:
        user_message = ChatMessage(role="user", content=user_message)
        self.thread.messages.append(user_message)
        # If the thread was empty, and now it's not, remove the ConversationOptions.
        if len(self.thread.messages) == 2:
            try:
                options = self.query_one(ConversationOptions)
            except NoMatches:
                log.error("Couldn't remove ConversationOptions as it wasn't found.")
            else:
                await options.remove()

        container = self.query_one(VerticalScroll)
        await container.mount(Chatbox(user_message))

        self.post_message(self.AgentResponseStarted())

        log.debug(
            f"First user message received in "
            f"conversation with model {self.chosen_model.name!r}"
        )

        streaming_response = await openai.ChatCompletion.acreate(
            model=self.chosen_model.name,
            messages=self.thread.messages,
            stream=True,
        )

        response_chatbox = Chatbox(
            message=ChatMessage(role="assistant", content=""),
            classes="assistant-message",
        )
        await container.mount(response_chatbox)

        response_stream_lock = asyncio.Lock()

        async def handle_next_event():
            async with response_stream_lock:
                try:
                    event = await streaming_response.__anext__()
                    choice = event["choices"][0]
                    if choice.get("finish_reason") in {"stop", "length",
                                                       "content_filter"}:
                        self.post_message(self.AgentResponseComplete())
                        if self._response_stream_timer is not None:
                            self._response_stream_timer.stop()
                        return
                    response_chatbox.append_chunk(event)
                except (StopAsyncIteration, IndexError):
                    self.post_message(self.AgentResponseComplete())
                    if self._response_stream_timer is not None:
                        self._response_stream_timer.stop()

        self._response_stream_timer = self.set_interval(0.05, handle_next_event)

    def on_conversation_agent_response_complete(self) -> None:
        timer = self._response_stream_timer
        if timer is not None:
            timer.stop()

    def compose(self) -> ComposeResult:
        yield ConversationHeader(title="Untitled Chat")
        with VerticalScroll() as vertical_scroll:
            vertical_scroll.can_focus = False
            yield ConversationOptions()

            # TODO - check if conversation is pre-existing.
            #  If it already exists, load it here.
            #  If it's a new empty conversation, show the options for a new conversation.

    class AgentResponseStarted(Message):
        pass

    class AgentResponseComplete(Message):
        pass
