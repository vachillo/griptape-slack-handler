# Griptape Cloud Structure-as-a-Slackbot

Fully deployable slack event handler deployable to a Griptape Cloud Structure.


## Environment Setup
- Install [Poetry](https://python-poetry.org/docs/#installation).
- Run `make setup`.
- Create `.env`, `.env.secret`, and `.env.tasks`. See the `*.example` files to see what is needed.
- (Optional) Create `.env.dev`. `.env.dev.secret` if you want to deploy to a dev Structure.


## Deploying your Structure code to Griptape Cloud
- Ensure that your [Github Account is connected to your Griptape Cloud account](https://cloud.griptape.ai/account).
- Create a [Griptape Cloud Structure](https://cloud.griptape.ai/structures/create) that points to this Github repository.
    - Make sure to point the Structure at the `griptape_cloud` branch so that the `make deploy-griptape` command can be used.
    - (Optional) Create another structure that points at the `griptape_cloud_dev` branch.
- Copy the Structure ID to the `.env.tasks` file with the variable name `GT_CLOUD_STRUCTURE_ID`.
    - (Optional) Copy the Dev Structure ID to the `.env.tasks` file with the variable name `GT_CLOUD_STRUCTURE_ID_DEV`.
- Run `make deploy-griptape-env` to create/update the environment variables on the Structure, and create any Griptape Cloud Secrets.
- Run `make deploy-griptape` to deploy the code on the current branch to the `griptape_cloud` branch.

## Creating the Slack App Integration
- Go to [Griptape Cloud Integrations](https://cloud.griptape.ai/structures/create) and fill out the form for creating a Slack integration.
    - Skip the entry about Bot Token and Signing Secret, we will update those later.
    - If you have already created your Slack Bot Structure, select it now under the "Structures" field.
- Copy the Slack App Manifest on the Integration config page.
- Go to your [Slack Apps Page](https://api.slack.com/apps) and Press "Create New App" -> "From a manifest".
- Paste in the Slack App Manifest, and click through until the app is created.
- Get the Signing Secret from the "Basic Information" tab from your newly created App.
- Go back to your integration page on Griptape Cloud and type in a secret name under "Slack App Secret" and hit enter.
- Paste in the value of the Signing Secret.
- Go back to your Slack App and press the "OAuth & Permissions" tab.
- Click the "Install to <workspace>" button, and click through to install the App into your Slack workspace.
- Copy the newly created Bot Token.
- Go back to your integration page on Griptape Cloud and type in a secret name under "Slack Bot Token" and hit enter.
- Paste in the value of the Bot Token.
- Lastly, go back to your slack app and press the "Event Subscriptions" tab.
- Hit "retry" next to the URL displayed in the field. It should have a green checkmark and say "Verified".

That's it! Now find your app in Slack and start chatting. It can be added to channels and messaged in private chats.

## Slack Bot Runtime Configuration

The bot will always respond with a three-dots gif to indicate it has started processing messages. It will then update this message over time, explaining its actions, and then ultimately overwrite the message with its final response.

There are a few ways to configure other behavior of the bot at runtime.

### Dynamic Rulesets

Using the `GriptapeCloudRulesetDriver` allows the bot to pull in Rulesets for every event that comes through. For every message, the bot will reach out to Griptape Cloud and try to find [Rulesets](https://cloud.griptape.ai/rulesets) that are aliased with the following values:
- Slack App ID
- Slack Team ID
- Slack Channel ID
- Slack User ID

Simply create a Griptape Cloud Ruleset and set the `alias` field to any one of those values, and the bot will find and use them.

### Conversation Memory

The bot will always respond in a Slack thread, creating a new one if needed. Outside of a DM, the bot will only respond if explicitly tagged with `@bot_name`. However, the bot is picking up other messages and storing them in a Griptape Cloud [Thread](https://cloud.griptape.ai/threads), and will be able to understand previous context if tagged in a message later in a Slack thread.

### Experimental

#### Dynamic Tool Selection

Creating a "Kitchen Sink" Agent with Griptape is really easy, but sometimes the LLM can get confused if it is given too many instructions. The [`get_tools`](griptape_slack_handler/griptape_tool_box.py) function with parameter `dyanamic=True` will prompt the LLM to decide which tools it should use to accomplish a given input, and those tools will be passed to the final "Kitchen Sink" agent that will respond to the user. It will use other context, such as conversation history, to make its decision.

This can be enabled by setting `"enable_toolbox": "true"` in the metadata of any Ruleset that gets pulled in.

#### Streaming Responses

Responses from the Griptape Agent can be streamed token-by-token for faster perceived response times. These tokens will be batched and sent as larger message chunks back to slack, updating the bot's initial response message over time.

This can be enabled by setting `"stream": "true"` in the metadata of any Ruleset that gets pulled in.
