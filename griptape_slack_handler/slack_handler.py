import os
import logging
from slack_bolt import App, BoltRequest
from slack_sdk import WebClient

from .slack_util import (
    error_payload,
    send_message,
    send_message_blocks,
    typing_message,
    react_to_message,
    integer_to_number_string,
)
from .griptape_handler import (
    agent,
    get_rulesets,
    try_add_to_thread,
    is_relevant_response,
)
from .griptape_event_handlers import event_listeners
from .features import (
    stream_output_enabled,
    thread_history_enabled,
    shadow_user_enabled,
    shadow_user_always_respond_enabled,
    assistant_typing_message_enabled,
)

logger = logging.getLogger("griptape_slack_handler")

app: App = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
    process_before_response=True,  # required because of threading
    request_verification_enabled=False,  # required because of threading
    token_verification_enabled=False,  # required because of threading
)

SHADOW_USER_ID = os.environ.get("SHADOW_USER_ID")

### Slack Event Handlers ###


@app.event("message")
def message(body: dict, payload: dict, client: WebClient):
    logger.debug(f"Handling message event type: {payload.get('subtype')}")
    # only respond to direct messages, otherwise the bot
    # will respond to every message in every channel it is in
    if payload.get("channel_type") == "im":
        logger.debug("Responding to direct message")
        typing_message(
            message="recieved the message...",
            thread_ts=payload.get("thread_ts", payload["ts"]),
            channel=payload["channel"],
            client=client,
        )
        respond_in_thread(body, payload, client)
    # if the message body @ mentions the shadow user, then call the shadow_resopnse function
    elif (
        shadow_user_enabled()
        and SHADOW_USER_ID is not None
        and SHADOW_USER_ID in payload.get("text", "")
    ):
        logger.debug("Shadow user mentioned")
        typing_message(
            message="recieved the message...",
            thread_ts=payload.get("thread_ts", payload["ts"]),
            channel=payload["channel"],
            client=client,
        )
        shadow_respond_in_thread(body, payload, client)
    elif payload.get("subtype") != "bot_message" and thread_history_enabled():
        logger.debug("Adding message to thread without responding")
        # add the message to the cloud thread
        # so the bot can use it for context when
        # responding to future messages in a thread
        try_add_to_thread(
            payload["text"],
            thread_alias=payload.get("thread_ts", payload["ts"]),
            user_id=payload["user"],
        )


@app.event("app_mention")
def app_mention(body: dict, payload: dict, client: WebClient):
    logger.debug("Handling app_mention event")
    typing_message(
        message="recieved the message...",
        thread_ts=payload.get("thread_ts", payload["ts"]),
        channel=payload["channel"],
        client=client,
    )
    respond_in_thread(body, payload, client)


def shadow_respond_in_thread(body: dict, payload: dict, client: WebClient):
    thread_ts = payload.get("thread_ts", payload["ts"])

    try:
        rulesets = get_rulesets(
            user_id=payload["user"],
            channel_id=payload["channel"],
            team_id=body["team_id"],
            app_id=body["api_app_id"],
        )
        logger.debug(f"Loaded {len(rulesets)} rulesets")
        logger.debug(
            f"Rulesets names: {', '.join([ruleset.name for ruleset in rulesets])}"
        )

        agent_output = agent(
            payload["text"],
            thread_alias=thread_ts,
            user_id=payload["user"],
            rulesets=rulesets,
            event_listeners=event_listeners(
                stream=False,
                web_client=client,
                thread_ts=thread_ts,
                channel=payload["channel"],
                typing_message=assistant_typing_message_enabled(),
            ),
            stream=False,
        )
    except Exception:
        logger.exception("Error while processing shadow response")
        return

    typing_message(
        "is deciding to respond...",
        thread_ts=thread_ts,
        channel=payload["channel"],
        client=client,
    )
    # use the tuple from is_relevant_response to determine if the response is relevant
    if (
        shadow_user_always_respond_enabled()
        or (score_tuple := is_relevant_response(payload["text"], agent_output))[0]
    ):
        logger.debug("Shadow response is relevant, sending")
        send_message_blocks(
            agent_output,
            thread_ts=thread_ts,
            channel=payload["channel"],
            client=client,
        )
    else:
        logger.debug("Shadow response not relevant, not sending")
        typing_message(thread_ts=thread_ts, channel=payload["channel"], client=client)
        react_to_message(
            "zoom-eyes", channel=payload["channel"], ts=payload["ts"], client=client
        )
        react_to_message(
            integer_to_number_string(score_tuple[1]),
            channel=payload["channel"],
            ts=payload["ts"],
            client=client,
        )


def respond_in_thread(body: dict, payload: dict, client: WebClient):
    team_id = body["team_id"]
    app_id = body["api_app_id"]
    thread_ts = payload.get("thread_ts", payload["ts"])

    stream = stream_output_enabled()

    try:
        rulesets = get_rulesets(
            user_id=payload["user"],
            channel_id=payload["channel"],
            team_id=team_id,
            app_id=app_id,
        )
        logger.debug(f"Loaded {len(rulesets)} rulesets")
        logger.debug(
            f"Rulesets names: {', '.join([ruleset.name for ruleset in rulesets])}"
        )

        agent_output = agent(
            payload["text"],
            thread_alias=thread_ts,
            user_id=payload["user"],
            rulesets=rulesets,
            event_listeners=event_listeners(
                stream=stream,
                web_client=client,
                thread_ts=thread_ts,
                channel=payload["channel"],
                typing_message=assistant_typing_message_enabled(),
            ),
            stream=stream,
        )
    except Exception as e:
        logger.exception("Error while processing response")
        send_message(
            **error_payload(str(e)),
            thread_ts=thread_ts,
            channel=payload["channel"],
            channel_type=payload.get("channel_type"),
        )
        return

    # Assuming that the response is already sent if its being streamed
    if not stream:
        logger.debug("Sending response")
        send_message_blocks(
            agent_output,
            thread_ts=thread_ts,
            channel=payload["channel"],
            client=client,
        )


def handle_slack_event(body: str, headers: dict) -> dict:
    req = BoltRequest(body=body, headers=headers)
    bolt_response = app.dispatch(req=req)
    return {
        "status": bolt_response.status,
        "body": bolt_response.body,
        "headers": bolt_response.headers,
    }
