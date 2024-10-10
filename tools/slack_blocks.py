from .util import pretty_chunking_block


LOADERS_URL = "https://dim8ibqgp8o75.cloudfront.net"
ERROR_PNG = f"{LOADERS_URL}/error.png"
THINKING_GIF = f"{LOADERS_URL}/thinking.gif"


def thinking_block():
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


def thought_blocks(thought: str):
    """Gets a list of blocks with the thought bubble."""
    return markdown_blocks(f":thought_balloon: _{thought}_")


def markdown_blocks(text: str):
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


def error_block(error: str):
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
