from typing import Generator

SLACK_MAX_BLOCK_CHARS = 3000
SLACK_MAX_TEXT_CHARACTERS = 40_000
SLACK_MAX_BLOCKS = 50


def pretty_chunking(
    text: str, max_chunk_size: int, min_chunk_size: int
) -> Generator[str, None, None]:
    """
    Split the text into chunks that are less than the slack max character limit.
    Try to split on a period or newline if possible
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
            i = max_chunk_size

        yield text[:i]
        text = text[i:]


def pretty_chunking_text(text: str) -> Generator[str, None, None]:
    return pretty_chunking(
        text, SLACK_MAX_TEXT_CHARACTERS, SLACK_MAX_TEXT_CHARACTERS - 200
    )


def pretty_chunking_block(text: str) -> Generator[str, None, None]:
    return pretty_chunking(text, SLACK_MAX_BLOCK_CHARS, SLACK_MAX_BLOCK_CHARS - 1000)
