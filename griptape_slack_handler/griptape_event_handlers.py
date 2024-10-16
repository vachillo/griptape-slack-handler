from __future__ import annotations
from typing import Optional
import logging

from griptape.events import (
    EventListener,
    StartStructureRunEvent,
    StartActionsSubtaskEvent,
    FinishActionsSubtaskEvent,
    CompletionChunkEvent,
)
from .slack_event_listener_driver import SlackEventListenerDriver
from .slack_util import thought_block, action_block, emoji_block

logger = logging.getLogger()


def event_listeners(*, stream: bool, **kwargs) -> list[EventListener]:
    # if stream is True, we will use the batched driver to deliver chunk events
    # and continuously update the slack message
    if stream:
        driver = SlackEventListenerDriver(**kwargs, batched=True, batch_size=100)
        return [
            EventListener(
                stream_handler,
                event_types=[CompletionChunkEvent],
                event_listener_driver=driver,
            )
        ]

    # WIP: use event listeners to create different UXs of different actions the LLM is taking
    driver = SlackEventListenerDriver(**kwargs)
    return [
        EventListener(
            start_structure_handler,
            event_types=[StartStructureRunEvent],
            event_listener_driver=driver,
        ),
        EventListener(
            start_actions_subtask_handler,
            event_types=[StartActionsSubtaskEvent],
            event_listener_driver=driver,
        ),
        EventListener(
            finish_actions_subtask_handler,
            event_types=[FinishActionsSubtaskEvent],
            event_listener_driver=driver,
        ),
    ]


def start_structure_handler(event: StartStructureRunEvent) -> Optional[dict]:
    return {
        "text": "Starting...",
        "blocks": [emoji_block(":envelope:", "Reading the data...")],
    }


def start_actions_subtask_handler(event: StartActionsSubtaskEvent) -> Optional[dict]:
    if event.subtask_actions is None:
        return None
    blocks = [
        thought_block(
            event.subtask_thought if event.subtask_thought is not None else "Thought..."
        )
    ]
    blocks.extend([action_block(str(action)) for action in event.subtask_actions])
    return {"blocks": blocks, "text": "Thought..."}


def finish_actions_subtask_handler(event: FinishActionsSubtaskEvent) -> Optional[dict]:
    return {
        "text": "Finishing...",
        "blocks": [emoji_block(":pencil:", "Analyzing the data...")],
    }


def stream_handler(event: CompletionChunkEvent) -> Optional[dict]:
    # WIP. needs to be merged in griptape
    if event.meta.get("type") == "action":
        # drop action events
        return None
    return {
        "text": event.token,
    }
