import os
import logging
from slack_bolt import App, Say, BoltRequest
from slack_sdk import WebClient

from tools.slack_blocks import thinking_block, markdown_blocks_list, error_block

from tools import agent

logger = logging.getLogger()

app: App = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
    process_before_response=True,  # required
)

### Slack Event Handlers ###


@app.event("message")
def message(payload: dict, say: Say, client: WebClient):
    # only respond to direct messages
    # this gets triggered for every message in a channel
    if payload.get("channel_type") == "im":
        respond_in_thread(payload, say, client)


@app.event("app_mention")
def app_mention(payload: dict, say: Say, client: WebClient):
    respond_in_thread(payload, say, client)


def respond_in_thread(payload: dict, say: Say, client: WebClient):
    # respond to the user in thread
    thread_ts = payload.get("thread_ts", payload["ts"])
    thinking_res = say(
        text="Thinking...",
        blocks=[thinking_block()],
        thread_ts=thread_ts,
    )
    ts = thinking_res["ts"]

    stream = True  # toggle this changes slack app behavior
    try:
        # call the agent
        agent_output = agent(
            payload["text"],
            thread_alias=thread_ts,
            user_id=payload["user"],
            channel_id=payload["channel"],
            web_client=client,
            ts=ts,
            thread_ts=thread_ts,
            stream=stream,
        )
    except Exception as e:
        logger.error(e)
        client.chat_postMessage(
            blocks=[error_block(str(e))],
            ts=ts,
            text="Error while processing response",
            channel=payload["channel"],
            channel_type=payload.get("channel_type"),
        )
        return

    # Assuming that the response is already sent if its being streamed
    if not stream:
        for i, blocks in enumerate(markdown_blocks_list(agent_output)):
            if i == 0:
                client.chat_update(
                    text=agent_output,
                    blocks=blocks,
                    ts=thinking_res.get("ts"),
                    channel=payload["channel"],
                )
            else:
                client.chat_postMessage(
                    text=agent_output,
                    blocks=blocks,
                    thread_ts=thread_ts,
                    channel=payload["channel"],
                )


def handle_slack_event(body: str, headers: dict) -> dict:
    req = BoltRequest(body=body, headers=headers)
    bolt_response = app.dispatch(req=req)
    return {
        "status": bolt_response.status,
        "body": bolt_response.body,
        "headers": bolt_response.headers,
    }
