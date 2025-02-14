from griptape_slack_handler.slack_handler import handle_slack_event
import json

def slack_function(body: dict, headers):
    return handle_slack_event(json.dumps(body), headers)
