from __future__ import annotations

import json
from attrs import define, field, Factory
from typing import Optional, TYPE_CHECKING
import requests
from schema import Schema, Literal

from griptape.artifacts import JsonArtifact, InfoArtifact
from griptape.utils.decorators import activity
from griptape.tools import BaseTool

from griptape_slack_handler.griptape.giphy_event import GiphyEvent


@define
class GiphyTool(BaseTool):
    """
    A tool that searches for gifs using the Giphy API
    """

    api_key: str = field()
    base_url: str = field(default="https://api.giphy.com/v1/gifs")
    max_results: int = field(default=5)
    send_event: bool = field(default=True)

    @activity(
        config={
            "description": "Can be used for getting a random gif. This should always be used for every response.",
            "schema": Schema(
                {
                    Literal(
                        "tag",
                        description="The search query to use when searching for a random gif.",
                    ): str,
                },
            ),
        },
    )
    def random_gif(self, tag: str) -> JsonArtifact | InfoArtifact:
        """
        Searches for gifs using the Giphy API
        """
        from griptape.events import EventBus

        response = requests.get(
            f"{self.base_url}/random",
            params={
                "api_key": self.api_key,
                "q": tag,
                "limit": self.max_results,
            },
        )
        response.raise_for_status()

        if self.send_event:
            EventBus.publish_event(
                GiphyEvent(
                    url=response.json()["data"]["images"]["downsized_large"]["url"],
                    title=response.json()["data"]["title"],
                    tag=tag,
                )
            )

            return InfoArtifact("Giphy event sent")

        return JsonArtifact(
            {
                "url": response.json()["data"]["url"],
                "title": response.json()["data"]["title"],
            }
        )
