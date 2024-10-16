import logging

from griptape.memory.structure.base_conversation_memory import BaseConversationMemory
from griptape.tools import BaseTool, WebScraperTool
from griptape.drivers import TrafilaturaWebScraperDriver
from griptape.loaders import WebLoader
from griptape.structures import Agent
from griptape.tasks import PromptTask
from griptape.rules import Rule
from griptape.memory.structure import ConversationMemory, Run

logger = logging.getLogger()


class ReadOnlyConversationMemory(ConversationMemory):
    def add_run(self, run: Run) -> BaseConversationMemory:
        return self


def get_tools(message: str, *, dynamic: bool = False) -> list[BaseTool]:
    tools_dict = _init_tools_dict()
    if not dynamic:
        return [tool for tool, _ in tools_dict.values()]

    tools_descriptions = {
        k: tool.activity_description(getattr(tool, activity_name))
        for k, (tool, activity_name) in tools_dict.items()
    }

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
    tool_names = output.split(", ") if output != "None" else []
    logger.info(f"Tools needed: {tool_names}")
    return [tools_dict[tool_name][0] for tool_name in tool_names]


def _init_tools_dict() -> dict[str, tuple[BaseTool, str]]:
    """
    Initializes the tools dictionary.
    The return value is a dictionary where the key is the tool name
    and the value is a tuple containing the Tool object and the name
    of the @activity decorated function to call.
    """
    # TODO: Add other tools here
    return {
        "web_scraper": (
            WebScraperTool(
                web_loader=WebLoader(web_scraper_driver=TrafilaturaWebScraperDriver()),
            ),
            "get_content",
        ),
    }
