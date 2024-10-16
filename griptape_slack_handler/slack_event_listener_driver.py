from __future__ import annotations
import logging
from attrs import define, field
from typing import TYPE_CHECKING

from griptape.drivers import BaseEventListenerDriver

if TYPE_CHECKING:
    from slack_sdk import WebClient
    from griptape.events import BaseEvent

log = logging.getLogger()


@define(kw_only=True)
class SlackEventListenerDriver(BaseEventListenerDriver):
    """A driver for listening to events from Slack.

    Attributes:
        web_client: The Slack WebClient to use for interacting with the Slack API.
        ts: The timestamp of the message to update.
        thread_ts: The timestamp of the thread.
        channel: The channel ID.
    """

    web_client: WebClient = field()
    ts: str = field()
    thread_ts: str = field()
    channel: str = field()
    batched: bool = field(default=False)
    _slack_responses: dict = field(factory=dict, init=False)

    def try_publish_event_payload_batch(self, event_payload_batch: list[dict]) -> None:
        new_text = "".join([event.get("text", "") for event in event_payload_batch])
        try:
            self._slack_responses[self.ts] = self.web_client.chat_update(
                text=self._slack_responses.get(self.ts, {}).get("text", "") + new_text,
                ts=self.ts,
                thread_ts=self.thread_ts,
                channel=self.channel,
            )
        except Exception:
            log.exception("Error updating message")
            res = self.web_client.chat_postMessage(
                text=new_text,
                thread_ts=self.thread_ts,
                channel=self.channel,
            )
            self._slack_responses[res["ts"]] = res
            self.ts = res["ts"]

    def try_publish_event_payload(self, event_payload: dict) -> None:
        try:
            if "blocks" in event_payload:
                event_payload["blocks"] = (
                    self._get_last_blocks() + event_payload["blocks"]
                )
            self._slack_responses[self.ts] = self.web_client.chat_update(
                **event_payload,
                ts=self.ts,
                thread_ts=self.thread_ts,
                channel=self.channel,
            )
        except Exception:
            log.exception("Error updating message")
            res = self.web_client.chat_postMessage(
                **event_payload,
                thread_ts=self.thread_ts,
                channel=self.channel,
            )
            self._slack_responses[res["ts"]] = res
            self.ts = res["ts"]

    def _get_last_blocks(self):
        return (
            self._slack_responses.get(self.ts, {}).get("message", {}).get("blocks", [])
        )
