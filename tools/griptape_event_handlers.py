from __future__ import annotations
import logging

from griptape.events import (
    EventListener,
    StartPromptEvent,
    StartActionsSubtaskEvent,
    FinishActionsSubtaskEvent,
    CompletionChunkEvent,
)
from griptape.utils import Stream
from .slack_event_listener_driver import SlackEventListenerDriver
from .slack_blocks import thought_blocks

logger = logging.getLogger()


def event_listeners(*, stream: bool, **kwargs) -> list[EventListener]:
    if stream:
        driver = SlackEventListenerDriver(**kwargs, batched=True, batch_size=100)
        return [
            EventListener(
                stream_handler,
                event_types=[CompletionChunkEvent],
                driver=driver,
            )
        ]

    driver = SlackEventListenerDriver(**kwargs)
    return [
        EventListener(
            start_prompt_handler, event_types=[StartPromptEvent], driver=driver
        ),
        EventListener(
            start_actions_subtask_handler,
            event_types=[StartActionsSubtaskEvent],
            driver=driver,
        ),
        EventListener(
            finish_actions_subtask_handler,
            event_types=[FinishActionsSubtaskEvent],
            driver=driver,
        ),
    ]


def start_prompt_handler(event: StartPromptEvent) -> dict:
    return {
        "text": "Starting prompt...",
        # dont publish the message for now
        "publish_message": False,
    }


def start_actions_subtask_handler(event: StartActionsSubtaskEvent) -> dict:
    blocks = [
        block
        for blocks in [thought_blocks(action) for action in event.subtask_actions]
        for block in blocks
    ]
    return {"blocks": blocks, "text": "Thought..."}


def finish_actions_subtask_handler(event: FinishActionsSubtaskEvent) -> dict:
    return {
        "text": "Finishing actions subtask...",
        # dont publish the message for now
    }


def stream_handler(event: CompletionChunkEvent) -> dict:
    return {
        "text": event.token,
    }
