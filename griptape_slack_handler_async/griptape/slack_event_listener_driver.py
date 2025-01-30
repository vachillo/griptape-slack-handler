from __future__ import annotations
import logging
from attrs import define, field, Factory
from typing import TYPE_CHECKING, Optional, Callable
import threading
import asyncio

from griptape.events import BaseEvent
from griptape.drivers import BaseEventListenerDriver
from griptape.tools import BaseTool

from ..slack_util import typing_message

if TYPE_CHECKING:
    from slack_sdk.web.async_client import AsyncWebClient

log = logging.getLogger()


@define(kw_only=True)
class SlackEventListenerDriver(BaseEventListenerDriver):
    """
    A driver for sending messages back to Slack.

    Attributes:
        web_client: The Slack WebClient to use for interacting with the Slack API.
        ts: The timestamp of the message to update.
        thread_ts: The timestamp of the thread.
        channel: The channel ID.
    """

    web_client: AsyncWebClient = field()
    thread_ts: str = field()
    channel: str = field()
    disable_blocks: bool = field(default=False)
    ts: Optional[str] = field(default=None)
    batched: bool = field(default=False)

    _slack_responses: dict = field(factory=dict, init=False)
    _thread_lock: threading.Lock = field(factory=threading.Lock, init=False)

    def try_publish_event_payload_batch(self, event_payload_batch: list[dict]) -> None:
        """Only used for streaming events."""
        with self._thread_lock:
            new_text = "".join([event.get("text", "") for event in event_payload_batch])
            try:
                if self.ts is None:
                    res = asyncio.run(
                        self.web_client.chat_postMessage(
                            text=new_text,
                            thread_ts=self.thread_ts,
                            channel=self.channel,
                        )
                    )
                    self._slack_responses[res["ts"]] = res
                    self.ts = res["ts"]
                else:
                    res = self._slack_responses[self.ts] = asyncio.run(
                        self.web_client.chat_update(
                            text=self._slack_responses.get(self.ts, {}).get("text", "")
                            + new_text,
                            ts=self.ts,
                            thread_ts=self.thread_ts,
                            channel=self.channel,
                        )
                    )
                self._slack_responses[self.ts] = res
            except Exception:
                log.exception("Error updating message")
                res = asyncio.run(
                    self.web_client.chat_postMessage(
                        text=new_text,
                        thread_ts=self.thread_ts,
                        channel=self.channel,
                    )
                )
                self._slack_responses[res["ts"]] = res
                self.ts = res["ts"]

    def try_publish_event_payload(self, event_payload: dict) -> None:
        with self._thread_lock:
            payload = {**event_payload}
            try:
                if "blocks" in event_payload and not self.disable_blocks:
                    payload["blocks"] = (
                        self._get_last_blocks() + event_payload["blocks"]
                    )
                    if self.ts is None:
                        res = asyncio.run(
                            self.web_client.chat_postMessage(
                                **payload,
                                thread_ts=self.thread_ts,
                                channel=self.channel,
                            )
                        )
                        self._slack_responses[res["ts"]] = res.data
                        self.ts = res["ts"]
                    else:
                        res = asyncio.run(
                            self.web_client.chat_update(
                                **payload,
                                ts=self.ts,
                                thread_ts=self.thread_ts,
                                channel=self.channel,
                            )
                        )

                    self._slack_responses[res["ts"]] = res.data
                    return
                else:
                    asyncio.run(
                        typing_message(
                            message=payload.get("text", ""),
                            thread_ts=self.thread_ts,
                            channel_id=self.channel,
                            client=self.web_client,
                        )
                    )

            except Exception:
                log.exception("Error updating message")
                res = asyncio.run(
                    self.web_client.chat_postMessage(
                        **event_payload,
                        thread_ts=self.thread_ts,
                        channel=self.channel,
                    )
                )
                self._slack_responses[res["ts"]] = res.data
                self.ts = res["ts"]

    def _get_last_blocks(self):
        return (
            self._slack_responses.get(self.ts, {}).get("message", {}).get("blocks", [])
        )
