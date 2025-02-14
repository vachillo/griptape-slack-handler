from griptape_slack_handler.slack_handler import handle_slack_event

def slack_function(raw_body, headers):
    return handle_slack_event(raw_body, headers)
