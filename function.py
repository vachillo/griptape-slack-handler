from griptape_slack_handler.slack_handler import handle_slack_event

def slack_function(body, headers):
    return handle_slack_event(body, headers)
