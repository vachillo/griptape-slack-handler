from __future__ import annotations

import os
from typing import List, Optional as OptionalType

from schema import Schema, Literal, Optional
from attr import Factory, define, field
from griptape.artifacts import (
    TextArtifact,
    ErrorArtifact,
    ListArtifact,
    InfoArtifact,
)
from griptape.utils.decorators import activity
from griptape.tools import BaseTool
from github import Auth, Github, ContentFile


def _common_schema() -> dict:
    return {
        Literal(
            "repo",
            description="The repository to get the contents from.",
        ): str,
        Literal(
            "owner",
            description="The owner or organization of the repository.",
        ): str,
    }


@define
class GitHubUserTool(BaseTool):
    """
    A tool for interacting with the Github as a user.
    """

    client: Github = field(
        default=Factory(lambda self: self._get_client(), takes_self=True)
    )

    @activity(
        config={
            "description": "Can be used to get file contents in the Github repository.",
            "schema": Schema(
                {
                    Literal(
                        "path",
                        description="The path in the repository.",
                    ): str,
                    **_common_schema(),
                    Optional(
                        Literal(
                            "ref",
                            description="The ref to use for the repository. Default is 'main'.",
                        )
                    ): str,
                }
            ),
        }
    )
    def get_repo_contents(
        self, path: str, repo: str, owner: str, ref: str = "main"
    ) -> ListArtifact | TextArtifact | ErrorArtifact:
        try:
            contents: List[ContentFile.ContentFile] | ContentFile.ContentFile = (
                self.client.get_repo(f"{owner}/{repo}").get_contents(path, ref=ref)
            )

            if isinstance(contents, list):
                artifacts = []
                for content in contents:
                    artifacts.append(
                        self._convert_github_content_to_artifact(
                            content, list_mode=False
                        )
                    )
                return ListArtifact(artifacts)
            else:
                return self._convert_github_content_to_artifact(
                    contents, list_mode=False
                )

        except Exception as e:
            return ErrorArtifact(f"error getting content: {e}")

    @activity(
        config={
            "description": "Can be used to comment on a pull request or issue in the Github repository.",
            "schema": Schema(
                {
                    Literal(
                        "pull_request_or_issue_id",
                        description="The ID of the pull request or issue to comment on.",
                    ): str,
                    Literal(
                        "comment",
                        description="The comment to post on the PR.",
                    ): str,
                    **_common_schema(),
                },
            ),
        }
    )
    def create_issue_comment(
        self, pull_request_or_issue_id: str, comment: str, repo: str, owner: str
    ) -> InfoArtifact | ErrorArtifact:
        try:
            issue_comment = (
                self.client.get_repo(f"{owner}/{repo}")
                .get_issue(int(pull_request_or_issue_id))
                .create_comment(comment)
            )
            return InfoArtifact(f"comment created: {issue_comment.html_url}")
        except Exception as e:
            return ErrorArtifact(f"error creating comment: {e}")

    @activity(
        config={
            "description": "Can be used to approve or comment on a pull request in the Github repository. The files in the pull request should be reviewed before approving.",
            "schema": Schema(
                {
                    Literal(
                        "pull_request_id",
                        description="The ID of the pull request.",
                    ): str,
                    Optional(
                        Literal(
                            "comment",
                            description="A friendly comment for the pull request review. something like 'looks good' or 'nice work'. be creative and use only lowercase letters.",
                        )
                    ): str,
                    Literal(
                        "approve",
                        description="Whether to approve the pull request or not.",
                    ): bool,
                    **_common_schema(),
                },
            ),
        }
    )
    def review_pull_request(
        self,
        pull_request_id: str,
        approve: bool,
        repo: str,
        owner: str,
        comment: OptionalType[str] = None,
    ) -> InfoArtifact | ErrorArtifact:
        try:
            pull_request = self.client.get_repo(f"{owner}/{repo}").get_pull(
                int(pull_request_id)
            )
            event = "APPROVE" if approve else "COMMENT"
            if comment is not None:
                pull_request.create_review(body=comment, event=event)
            else:
                pull_request.create_review(event=event)

            return InfoArtifact("pull request approved")
        except Exception as e:
            return ErrorArtifact(f"error approving pull request: {e}")

    # activity to read PR data
    @activity(
        config={
            "description": "Can be used to get data about what is changing in a pull request.",
            "schema": Schema(
                {
                    Literal(
                        "pull_request_id",
                        description="The ID of the pull request to get data from.",
                    ): str,
                    **_common_schema(),
                },
            ),
        }
    )
    def get_pull_request_data(
        self, pull_request_id: str, repo: str, owner: str
    ) -> ListArtifact[TextArtifact] | ErrorArtifact:
        try:
            pull_request_files = (
                self.client.get_repo(f"{owner}/{repo}")
                .get_pull(int(pull_request_id))
                .get_files()
            )
            pull_request_description = (
                self.client.get_repo(f"{owner}/{repo}")
                .get_pull(int(pull_request_id))
                .body
            )
            return ListArtifact(
                [
                    TextArtifact(f"Description: {pull_request_description}"),
                    *[
                        TextArtifact(f"File Patch: {f.patch}")
                        for f in pull_request_files
                    ],
                ]
            )
        except Exception as e:
            return ErrorArtifact(f"error getting pull request data: {e}")

    def _convert_github_content_to_artifact(
        self, content: ContentFile.ContentFile, list_mode: bool = False
    ) -> TextArtifact:
        if content.type == "dir":
            return TextArtifact(content.path)
        else:
            return (
                TextArtifact(content.decoded_content.decode("utf-8"))
                if not list_mode
                else TextArtifact(content.name)
            )

    def _get_client(self) -> Github:
        return Github(auth=Auth.Token(os.environ["GITHUB_PAT"]))
