import os
import logging
from typing import Optional

from slack_bolt.async_app import (
    AsyncAck,
    AsyncSay,
    AsyncRespond,
    AsyncBoltRequest,
    AsyncApp,
    AsyncSetStatus,
)
from slack_bolt.kwargs_injection.async_args import AsyncArgs
from slack_bolt import Assistant
from slack_bolt.async_app import AsyncAssistant

from slack_sdk.web.async_client import AsyncWebClient

from .slack_util import (
    error_payload,
    thinking_payload,
    markdown_blocks_list,
    typing_message,
)
from .griptape_handler import (
    agent,
    get_rulesets,
    try_add_to_thread,
    is_relevant_response,
)
from .griptape_event_handlers import event_listeners
from .features import (
    persist_thoughts_enabled,
    stream_output_enabled,
    thread_history_enabled,
)

logger = logging.getLogger()

assistant: AsyncAssistant = AsyncAssistant()

app: AsyncApp = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
    process_before_response=True,  # required
)
app.use(assistant)


SHADOW_USER_ID = os.environ.get("SHADOW_USER_ID")


## Async Slack Event Handler ##
@app.event("message")
async def async_message(
    body: dict,
    payload: dict,
    client: AsyncWebClient,
):
    if payload.get("channel_type") == "im":
        await typing_message(
            message="is thinking...",
            thread_ts=payload.get("thread_ts", payload["ts"]),
            channel_id=payload["channel"],
            client=client,
        )
        await async_respond_in_thread(body, payload, client)
    elif SHADOW_USER_ID is not None and SHADOW_USER_ID in payload.get("text", ""):
        await async_shadow_respond_in_thread(body, payload, client)
    elif payload.get("subtype") != "bot_message" and thread_history_enabled():
        await try_add_to_thread(
            payload["text"],
            thread_alias=payload.get("thread_ts", payload["ts"]),
            user_id=payload["user"],
        )


@app.event("app_mention")
async def async_app_mention(
    body: dict,
    payload: dict,
    client: AsyncWebClient,
):
    await typing_message(
        message="is thinking...",
        thread_ts=payload.get("thread_ts", payload["ts"]),
        channel_id=payload["channel"],
        client=client,
    )

    await async_respond_in_thread(body, payload, client)


async def async_shadow_respond_in_thread(
    body: dict, payload: dict, client: AsyncWebClient
):
    thread_ts = payload.get("thread_ts", payload["ts"])

    try:
        rulesets = await get_rulesets(
            user_id=payload["user"],
            channel_id=payload["channel"],
            team_id=body["team_id"],
            app_id=body["api_app_id"],
        )

        agent_output = await agent(
            payload["text"],
            thread_alias=thread_ts,
            user_id=payload["user"],
            rulesets=rulesets,
            event_listeners=[],
            stream=False,
        )
    except Exception as e:
        logger.exception("Error while processing response")
        return

    if await is_relevant_response(payload["text"], agent_output):
        logger.info("Shadow response is relevant, sending")
        for blocks in markdown_blocks_list(agent_output):
            await client.chat_postMessage(
                text=agent_output,
                blocks=blocks,
                thread_ts=thread_ts,
                channel=payload["channel"],
            )
    else:
        logger.info("Shadow response not relevant, not sending")


async def async_respond_in_thread(body: dict, payload: dict, client: AsyncWebClient):
    team_id = body["team_id"]
    app_id = body["api_app_id"]
    thread_ts = payload.get("thread_ts", payload["ts"])

    stream = stream_output_enabled()

    try:
        rulesets = await get_rulesets(
            user_id=payload["user"],
            channel_id=payload["channel"],
            team_id=team_id,
            app_id=app_id,
        )
        stream = stream or any(
            [ruleset.meta.get("stream", False) for ruleset in rulesets]
        )

        event_listeners_ = event_listeners(
            stream=stream,
            web_client=client,
            thread_ts=thread_ts,
            channel=payload["channel"],
            disable_blocks=True,
        )
        agent_output = await agent(
            payload["text"],
            thread_alias=thread_ts,
            user_id=payload["user"],
            rulesets=rulesets,
            event_listeners=event_listeners_,
            stream=stream,
        )
    except Exception as e:
        logger.exception("Error while processing response")
        await client.chat_postMessage(
            **error_payload(str(e)),
            thread_ts=thread_ts,
            channel=payload["channel"],
            channel_type=payload.get("channel_type"),
        )
        return

    ts = (
        event_listeners_[0].event_listener_driver.ts  # type: ignore
        if event_listeners_[0] is not None
        else None
    )
    if not stream:
        for i, blocks in enumerate(markdown_blocks_list(agent_output)):
            if i == 0 and ts is not None and not persist_thoughts_enabled():
                await client.chat_update(
                    text=agent_output,
                    blocks=blocks,
                    ts=ts,
                    channel=payload["channel"],
                )
            else:
                ts = (
                    await client.chat_postMessage(
                        text=agent_output,
                        blocks=blocks,
                        thread_ts=thread_ts,
                        channel=payload["channel"],
                    )
                )["ts"]


async def handle_slack_event(body: str, headers: dict) -> dict:
    req = AsyncBoltRequest(body=body, headers=headers)
    bolt_response = await app.async_dispatch(req=req)
    return {
        "status": bolt_response.status,
        "body": bolt_response.body,
        "headers": bolt_response.headers,
    }
