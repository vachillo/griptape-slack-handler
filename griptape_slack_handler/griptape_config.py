import os
import logging
from typing import Optional
import rich.logging
import logging

from griptape.configs import Defaults
from griptape.configs.drivers import AzureOpenAiDriversConfig
from griptape.drivers import (
    GriptapeCloudConversationMemoryDriver,
    GriptapeCloudRulesetDriver,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[rich.logging.RichHandler()],
    force=True,
)

# Set desired logging level for
logging.getLogger("griptape").setLevel(os.environ.get("LOG_LEVEL", logging.INFO))
logging.getLogger("griptape_slack_handler").setLevel(
    os.environ.get("LOG_LEVEL", logging.INFO)
)


def load_griptape_config() -> None:
    """Load the Default Griptape configuration. If no OPENAI_API_KEY is found, use Azure OpenAI drivers."""
    if "OPENAI_API_KEY" not in os.environ:
        from azure.identity import DefaultAzureCredential

        def azure_ad_token_provider():
            return (
                DefaultAzureCredential()
                .get_token("https://cognitiveservices.azure.com/.default")
                .token
            )

        Defaults.drivers_config = AzureOpenAiDriversConfig(
            azure_ad_token_provider=azure_ad_token_provider,
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )
        Defaults.drivers_config.prompt_driver.api_version = (
            "2024-08-01-preview"  # needed for structured output
        )

    Defaults.drivers_config.ruleset_driver = GriptapeCloudRulesetDriver(
        raise_not_found=False
    )
    Defaults.drivers_config.conversation_memory_driver = (
        GriptapeCloudConversationMemoryDriver()
    )


def set_thread_alias(thread_alias: Optional[str]) -> None:
    """Set the thread alias for the conversation memory driver."""
    Defaults.drivers_config.conversation_memory_driver.alias = thread_alias
