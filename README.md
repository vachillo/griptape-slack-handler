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
TODO



