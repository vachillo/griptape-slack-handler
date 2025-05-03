import sys
import json

if __name__ == "__main__":
    from griptape_slack_handler import handle_slack_event

    body, query, headers = sys.argv[1:4]
    res = handle_slack_event(body, json.loads(headers))

    if res["status"] >= 400:
        sys.exit(1)
