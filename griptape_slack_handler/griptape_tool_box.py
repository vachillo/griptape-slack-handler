import logging
import os
import requests

from griptape.memory.structure.base_conversation_memory import BaseConversationMemory
from griptape.tools import (
    BaseTool,
    WebScraperTool,
    WebSearchTool,
    DateTimeTool,
    GriptapeCloudToolTool,
)
from griptape.drivers import TrafilaturaWebScraperDriver, DuckDuckGoWebSearchDriver
from griptape.loaders import WebLoader
from griptape.structures import Agent
from griptape.tasks import PromptTask
from griptape.rules import Rule

from .griptape.read_only_conversation_memory import ReadOnlyConversationMemory
from .griptape.github_tool.tool import GitHubUserTool

logger = logging.getLogger("griptape_slack_handler")


def get_tools(message: str, *, dynamic: bool = False) -> list[BaseTool]:
    """
    Gets tools for the Agent to use. if dynamic=True, the LLM will decide what tools to use
    based on the user input and the conversation history.
    """
    tools_dict = _init_tools_dict()
    if not dynamic:
        return [tool for tool, _ in tools_dict.values()]

    tools_descriptions = {k: description for k, (_, description) in tools_dict.items()}

    # TODO: Use EvalEngine to determine which tools to use
    agent = Agent(
        tasks=[
            PromptTask(
                input="Given the input, what tools are needed to give an accurate response? Input: '{{ args[0] }}' Tools: {{ args[1] }}",
                rules=[
                    Rule(
                        "The tool name is the key in the tools dictionary, and the description is the value."
                    ),
                    Rule("Only respond with a comma-separated list of tool names."),
                    Rule("Do not include any other information."),
                    Rule("If no tools are needed, respond with 'None'."),
                ],
            ),
        ],
        conversation_memory=ReadOnlyConversationMemory(),
    )
    output = agent.run(message, tools_descriptions).output.value
    tool_names = output.split(",") if output != "None" else []
    return [tools_dict[tool_name.strip()][0] for tool_name in tool_names]


def _init_tools_dict() -> dict[str, tuple[BaseTool, str]]:
    """
    Initializes the tools dictionary.
    The return value is a dictionary where the key is the tool name
    and the value is a tuple containing the Tool object and a description
    of what the tool can do
    """
    cloud_tools_dict = {}

    if "GT_CLOUD_TOOL_IDS" in os.environ:
        cloud_tool_ids = os.environ["GT_CLOUD_TOOL_IDS"].split(",")
        tools = [GriptapeCloudToolTool(tool_id=tool_id) for tool_id in cloud_tool_ids]
        cloud_tools_dict = {
            tool.name: (tool, _get_cloud_tool_description(tool)) for tool in tools
        }
    return {
        "web_scraper": (
            WebScraperTool(
                web_loader=WebLoader(web_scraper_driver=TrafilaturaWebScraperDriver()),
            ),
            "Can be used find information on a web page. Should be used with web_search.",
        ),
        "web_search": (
            WebSearchTool(
                web_search_driver=DuckDuckGoWebSearchDriver(),
            ),
            "Can be used to search the web for information. Should be used with web_scraper.",
        ),
        "datetime": (
            DateTimeTool(),
            "Can be used to find the current date and time.",
        ),
        # "github": (
        #     GitHubUserTool(),
        #     "Can be used to interact with Github as a user.",
        # ),
        **cloud_tools_dict,
    }


def _get_cloud_tool_description(tool: GriptapeCloudToolTool) -> str:
    """
    Returns a description of the cloud tool.
    """
    return requests.get(
        f"{os.environ['GT_CLOUD_BASE_URL']}/api/tools/{tool.tool_id}"
    ).json()["description"]
