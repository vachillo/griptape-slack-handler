from __future__ import annotations

from typing import Generator, TYPE_CHECKING


if TYPE_CHECKING:
    from slack_sdk import WebClient


SLACK_MAX_BLOCK_CHARS = 3000
SLACK_MAX_TEXT_CHARACTERS = 40_000
SLACK_MAX_BLOCKS = 50

LOADERS_URL = "https://dim8ibqgp8o75.cloudfront.net"
ERROR_PNG = f"{LOADERS_URL}/error.png"
THINKING_GIF = f"{LOADERS_URL}/thinking.gif"


## Helper methods ##
def typing_message(
    message: str = "", *, thread_ts: str, channel: str, client: WebClient
) -> None:
    """Sets the message of the Assistant in the spot where you see 'user is typing...' in Slack. Typically it should start with 'is'. Defaults to an empty string to clear the message."""
    client.assistant_threads_setStatus(
        thread_ts=thread_ts,
        status=message,
        channel_id=channel,
    )


def integer_to_number_string(number: int) -> str:
    """Converts an integer to a number in english."""
    match number:
        case 0:
            return "zero"
        case 1:
            return "one"
        case 2:
            return "two"
        case 3:
            return "three"
        case 4:
            return "four"
        case 5:
            return "five"
        case 6:
            return "six"
        case 7:
            return "seven"
        case 8:
            return "eight"
        case 9:
            return "nine"
        case 10:
            return "ten"
        case _:
            return f"question"


def react_to_message(
    reaction: str, *, ts: str, channel: str, client: WebClient
) -> None:
    """Reacts to a message with an emoji."""
    client.reactions_add(
        name=reaction,
        channel=channel,
        timestamp=ts,
    )


def send_message_blocks(
    message: str, *, thread_ts: str, channel: str, client: WebClient
) -> None:
    """Sends a message to the channel. Block formatted messages are split into multiple messages if they exceed the block limit."""
    for blocks in markdown_blocks_list(message):
        send_message(
            blocks, message, thread_ts=thread_ts, channel=channel, client=client
        )


def send_message(
    blocks: list[dict],
    text: str,
    *,
    thread_ts: str,
    channel: str,
    client: WebClient,
    **kwargs,
) -> None:
    """Sends a message to the channel."""
    client.chat_postMessage(
        text=text,
        blocks=blocks,
        thread_ts=thread_ts,
        channel=channel,
        **kwargs,
    )


## Payload methods ##


def thinking_payload(**kwargs) -> dict:
    """Gets a payload with the thinking gif."""
    return {
        "blocks": [thinking_block(**kwargs)],
        "text": "Thinking...",
    }


def thought_payload(thought: str, **kwargs) -> dict:
    """Gets a payload with the thought bubble."""
    return {
        "blocks": thought_blocks(thought, **kwargs),
        "text": "Thought...",
    }


def markdown_payload(text: str, **kwargs) -> dict:
    """Gets a payload with the markdown text."""
    return {
        "blocks": markdown_blocks(text, **kwargs),
        "text": text,
    }


def error_payload(error: str, **kwargs) -> dict:
    """Gets a payload with the error message."""
    return {
        "blocks": [error_block(error, **kwargs)],
        "text": "Error while processing response",
    }


def action_payload(action: str, **kwargs) -> dict:
    """Gets a payload with the action bubble."""
    return {
        "blocks": action_blocks(action, **kwargs),
        "text": "Action...",
    }


## Block methods ##


def thinking_block(**kwargs) -> dict:
    """Gets a block with the thinking gif."""
    return {
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": THINKING_GIF,
                "alt_text": "Agent Thinking",
            },
        ],
    }


def error_block(error: str, **kwargs) -> dict:
    """Gets a block with the error message."""
    return {
        "type": "context",
        "elements": [
            {
                "type": "image",
                "image_url": ERROR_PNG,
                "alt_text": "Error",
            },
            {
                "type": "mrkdwn",
                "text": f"*Error while processing response:* {error}",
            },
        ],
    }


def emoji_block(emoji: str, text: str, *, format: bool = True, **kwargs) -> dict:
    """Gets a block with the emoji and text. Truncates the text to the max block text length."""
    return emoji_blocks(emoji, text, **kwargs)[0]


def action_block(action: str, **kwargs) -> dict:
    """Gets a block with the action bubble. Truncates the action to the max block text length."""
    return action_blocks(action, **kwargs)[0]


def thought_block(thought: str, **kwargs) -> dict:
    """Gets a block with the thought bubble. Truncates the thought to the max block text length."""
    return thought_blocks(thought, **kwargs)[0]


def markdown_block(text: str, **kwargs) -> dict:
    """Gets a block with the markdown text. Truncates the text to the max block text length."""
    return markdown_blocks(text, **kwargs)[0]


def emoji_blocks(emoji: str, text: str, *, format: bool = True, **kwargs) -> list[dict]:
    """Gets a block with the emoji and text."""
    return (
        markdown_blocks(f"{emoji} _{text}_", **kwargs)
        if format
        else markdown_blocks(f"{emoji} {text}", **kwargs)
    )


def action_blocks(action: str, **kwargs) -> list[dict]:
    """Gets a list of blocks with the action bubble."""
    return emoji_blocks(":hammer_and_wrench:", action, **kwargs)


def thought_blocks(thought: str, **kwargs) -> list[dict]:
    """Gets a list of blocks with the thought bubble."""
    return emoji_blocks(":thought_balloon:", thought, **kwargs)


def markdown_blocks(text: str, **kwargs) -> list[dict]:
    """Gets a list of markdown blocks with the max block text length."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": chunk,
            },
        }
        for chunk in pretty_chunking_block(text)
    ]


def markdown_blocks_list(text: str) -> list[list[dict]]:
    """Gets a list of a list of blocks with the slack max block limit of 50."""
    blocks = markdown_blocks(text)
    return [blocks[i : i + 50] for i in range(0, len(blocks), 50)]


## Chunking methods ##


def pretty_chunking(
    text: str, min_chunk_size: int, max_chunk_size: int
) -> Generator[str, None, None]:
    """
    Split the text into chunks based on the chunk sizes.
    Try to split on periods, newlines, or spaces if possible.
    """
    while True:
        if len(text) + text.count("\n") <= max_chunk_size:
            yield text
            return
        # find the nearest period or newline to split on
        i = max(
            [
                text.rfind(".", min_chunk_size, max_chunk_size),
                text.rfind("\n", min_chunk_size, max_chunk_size),
            ]
        )
        if i == -1:
            # if no period or newline found, split on space
            i = text.rfind(" ", min_chunk_size, max_chunk_size)

        if i == -1:
            # if no space found, split at max_chunk_size
            i = max_chunk_size

        yield text[:i]
        text = text[i:]


def pretty_chunking_text(text: str) -> Generator[str, None, None]:
    """
    Split the text into chunks that are less than the slack max character limit for text.
    """
    return pretty_chunking(
        text, SLACK_MAX_TEXT_CHARACTERS - 1000, SLACK_MAX_TEXT_CHARACTERS
    )


def pretty_chunking_block(text: str) -> Generator[str, None, None]:
    """
    Split the text into chunks that are less than the slack max character limit for blocks.
    """
    return pretty_chunking(text, SLACK_MAX_BLOCK_CHARS - 200, SLACK_MAX_BLOCK_CHARS)
