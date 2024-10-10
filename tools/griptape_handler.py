from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING
import logging

from griptape.configs import Defaults
from griptape.events import EventBus
from griptape.artifacts import ErrorArtifact
from griptape.loaders import WebLoader
from griptape.configs.drivers import AzureOpenAiDriversConfig
from griptape.rules import Ruleset
from griptape.structures import Agent
from griptape.tools import WebScraperTool
from griptape.drivers import (
    GriptapeCloudConversationMemoryDriver,
    GriptapeCloudRulesetDriver,
    TrafilaturaWebScraperDriver,
)

from azure.identity import DefaultAzureCredential

from .griptape_event_handlers import event_listeners
from .griptape_tool_box import get_tools

if TYPE_CHECKING:
    from griptape.events import EventListener
    from slack_sdk.web import WebClient


logger = logging.getLogger()


def azure_ad_token_provider():
    return (
        DefaultAzureCredential()
        .get_token("https://cognitiveservices.azure.com/.default")
        .token
    )


Defaults.drivers_config = AzureOpenAiDriversConfig(
    azure_ad_token_provider=azure_ad_token_provider,
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
)
Defaults.drivers_config.ruleset_driver = GriptapeCloudRulesetDriver(
    raise_not_found=False
)
Defaults.drivers_config.conversation_memory_driver = (
    GriptapeCloudConversationMemoryDriver()
)


def agent(
    message: str,
    *,
    thread_alias: Optional[str] = None,
    user_id: str,
    channel_id: str,
    web_client: WebClient,
    ts: str,
    thread_ts: str,
    stream: bool,
) -> str:
    Defaults.drivers_config.conversation_memory_driver.alias = thread_alias
    EventBus.add_event_listeners(
        event_listeners(
            stream=stream,
            web_client=web_client,
            ts=ts,
            thread_ts=thread_ts,
            channel=channel_id,
        )
    )

    agent = Agent(
        tools=get_tools(message),
        rulesets=[
            Ruleset(
                name=user_id,
            ),
            Ruleset(
                name=channel_id,
            ),
        ],
        stream=stream,
    )
    output = agent.run(message).output
    if isinstance(output, ErrorArtifact):
        raise ValueError(output.to_text())
    return output.to_text()
