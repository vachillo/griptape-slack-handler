import sys
import json
import rich.logging
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[
        rich.logging.RichHandler(
            tracebacks_code_width=500,
            tracebacks_show_locals=True,
            tracebacks_word_wrap=False,
            tracebacks_width=500,
            rich_tracebacks=True,
            locals_max_length=500,
            locals_max_string=500,
        )
    ],
    force=True,
)


if __name__ == "__main__":
    from griptape_slack_handler import handle_slack_event

    body, query, headers = sys.argv[1:4]
    ack_message_ts = sys.argv[4] if len(sys.argv) > 4 else None
    res = handle_slack_event(body, json.loads(headers), ack_message_ts)

    if res["status"] >= 400:
        sys.exit(1)
