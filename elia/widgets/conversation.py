from __future__ import annotations

from typing import Any

import openai
from rich.markdown import Markdown
from rich.text import Text
from textual import work, on
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.events import Timer
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Static

from elia.models import Thread, ChatMessage


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


class Chatbox(Widget):

    def __init__(
        self,
        message: ChatMessage | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        self.message = message

    def compose(self) -> ComposeResult:
        yield Static(Markdown(""))

    def append_chunk(self, chunk: Any):
        # If this Chatbox doesn't correspond to an OpenAI message,
        # make that connection now.
        if self.message is None:
            self.message = ChatMessage(
                id="",
                role="assistant",
                content="",
            )

        static = self.query_one(Static)
        static.update(chunk)


class Conversation(Widget):
    def __init__(self):
        super().__init__()

        # The thread initially only contains the system message.
        self.thread = Thread(messages=[
            ChatMessage(role="system", content="You are a helpful assistant.")
        ])

        self._response_stream_timer: Timer | None = None

    @work(exclusive=True)
    async def new_user_message(self, user_message: str) -> None:
        user_message = ChatMessage(
            role="user", content=user_message
        )
        self.thread.messages.append(user_message)
        container = self.query_one(VerticalScroll)
        await container.mount(Chatbox(user_message))

        self.post_message(self.AgentResponseStarted())

        streaming_response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=self.thread.messages,
            stream=True,
        )

        # {
        #     "choices": [
        #         {
        #             "delta": {
        #                 "content": "?"
        #             },
        #             "finish_reason": null,
        #             "index": 0
        #         }
        #     ],
        #     "created": 1683224430,
        #     "id": "chatcmpl-7CXr4jTdQfo8UGFYuHLaPhdsAAn4G",
        #     "model": "gpt-3.5-turbo-0301",
        #     "object": "chat.completion.chunk"
        # }

        response_chatbox = Chatbox(message=ChatMessage(role="assistant"))
        await container.mount(response_chatbox)

        async def handle_next_event():
            try:
                event = await streaming_response.__anext__()
                choice = event["choices"][0]
                if choice.get("finish_reason") in {"stop", "length", "content_filter"}:
                    return
                response_chatbox.append_chunk(event)
            except (StopAsyncIteration, IndexError):
                self.post_message(self.AgentResponseComplete())

        self.set_interval(0.5, handle_next_event)

    def on_conversation_agent_response_complete(self) -> None:
        timer = self._response_stream_timer
        if timer is not None:
            timer.stop()

    def compose(self) -> ComposeResult:
        vs = VerticalScroll()
        vs.can_focus = False
        yield vs

    class AgentResponseStarted(Message):
        pass

    class AgentResponseComplete(Message):
        pass
