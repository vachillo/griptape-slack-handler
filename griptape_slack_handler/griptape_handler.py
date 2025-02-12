from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING
import logging
import re
from schema import Schema, Literal

from griptape.events import EventBus
from griptape.artifacts import ErrorArtifact, TextArtifact
from griptape.rules import Ruleset, Rule, JsonSchemaRule
from griptape.structures import Agent
from griptape.memory.structure import ConversationMemory, Run
from griptape.engines import EvalEngine

from griptape_slack_handler.griptape_event_handlers import ToolEvent

from .griptape_tool_box import get_tools
from .griptape_config import load_griptape_config, set_thread_alias
from .features import dynamic_rulesets_enabled, dynamic_tools_enabled

if TYPE_CHECKING:
    from griptape.events import EventListener


logger = logging.getLogger("griptape_slack_handler")


load_griptape_config()


def try_add_to_thread(
    message: str, *, thread_alias: Optional[str] = None, user_id: str
) -> None:
    set_thread_alias(thread_alias)
    # find all the user_ids @ mentions in the message
    mentioned_user_ids = re.findall(r"<@([\w]+)>", message)
    rulesets = [Ruleset(name=mentioned_user) for mentioned_user in mentioned_user_ids]
    for ruleset in rulesets:
        # If the message is mentioning the bot, don't add it to the memory
        # because the bot will already be responding to the message,
        # and the message will be in conversation memory already
        if ruleset.meta.get("type") == "bot":
            return

    memory = ConversationMemory()
    # WIP. since messages that do not tag the bot are not being added to the cloud Thread,
    # the bot can miss context. This inserts those messages into the Thread, which
    # later can be used to provide context via ConversationMemory. this seems to work okay,
    # but it can confuse the LLM
    memory.add_run(
        Run(
            input=TextArtifact(
                f"Do not respond. Only use this message for future context. Message: 'user {user_id}: {message}'"
            ),
            output=TextArtifact(""),
        )
    )


def get_rulesets(**kwargs) -> list[Ruleset]:
    return (
        [Ruleset(name=value) for value in kwargs.values()]
        if dynamic_rulesets_enabled()
        else []
    )


def agent(
    message: str,
    *,
    thread_alias: Optional[str] = None,
    user_id: str,
    rulesets: list[Ruleset],
    event_listeners: list[EventListener],
    stream: bool,
) -> str:
    set_thread_alias(thread_alias)
    logger.debug(f"Setting thread alias to: {thread_alias}")
    EventBus.add_event_listeners(event_listeners)

    if dynamic_tools_enabled():
        logger.debug("Dynamic tools enabled")
        EventBus.publish_event(ToolEvent(tools=[], stream=stream), flush=True)
        tools = get_tools(message, dynamic=True)
        EventBus.publish_event(ToolEvent(tools=tools, stream=stream), flush=True)
    else:
        tools = get_tools(message, dynamic=False)

    logger.debug(f"Tools used for request: {', '.join([tool.name for tool in tools])}")

    agent = Agent(
        tools=tools,
        rulesets=rulesets,
        rules=[
            Rule(f"Slack user '{user_id}' has sent this message."),
            Rule(
                "You can respond to any Slack user with this syntax: <@user_id>, replace 'user_id' with the user's Slack Id."
            ),
        ],
        stream=stream,
    )
    output = agent.run(message).output
    if isinstance(output, ErrorArtifact):
        raise ValueError(output.to_text())
    return output.to_text()


def is_relevant_response(message: str, response: str) -> tuple[bool, int]:
    eval_engine = EvalEngine(
        evaluation_steps=[
            "If the actual_output is mostly just repeating the input, the score should be low.",
            "If the actual_output is unsure, the score should be low.",
            "If the actual_output does not have any useful information, the score should be low.",
            "If the actual_output is telling the user it can't do something, the score should be low.",
        ]
    )
    score, reason = eval_engine.evaluate(input=message, actual_output=response)
    logger.debug(f"EvalEngine score: {score}, reason: {reason}")
    if score > 0.8:
        logger.debug("Response is relevant")
        return True, int(score * 10)

    logger.debug("Response is not relevant")
    return False, int(score * 10)
