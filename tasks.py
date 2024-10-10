from invoke.tasks import task
from dotenv import load_dotenv
from dotenv.main import DotEnv
import os
import json
import requests

log = lambda c, msg: c.run(f"echo '{msg}'", pty=True)


@task
def deploy_griptape(c, dev=False):
    """Deploy to griptape cloud"""
    env_file = DotEnv(f".env.tasks").dict()
    structure_var_name = f"GT_CLOUD_STRUCTURE_ID{'_DEV' if dev else ''}"
    if env_file.get(structure_var_name) is None:
        raise ValueError(f"{structure_var_name} not found in .env.tasks file")
    diff = True
    try:
        c.run(f'git add . && git commit -m "Deploy"', hide=True)
    except:
        diff = False
    c.run(
        f"git push origin $(git branch --show-current):griptape_cloud{"_dev" if dev else ""} --force",
        hide=True,
    )
    if diff:
        c.run("git reset HEAD~1", hide=True)

    log(c, "Deployed to griptape cloud")


@task
def deploy_griptape_env(c, dev=False):
    """Deploy environment to griptape cloud"""
    load_dotenv(".env.tasks")

    host = os.getenv(
        f"GT_CLOUD_HOST{'_DEV' if dev else ''}", "https://cloud.griptape.com"
    )
    api_key = os.getenv(
        f"GT_CLOUD_API_KEY{'_DEV' if dev else ''}", os.getenv("GT_CLOUD_API_KEY")
    )
    structure_id = os.getenv(f"GT_CLOUD_STRUCTURE_ID{'_DEV' if dev else ''}")

    secrets_res = _call_griptape_cloud(host, "get", "/api/secrets", api_key)
    secrets_res.raise_for_status()
    secrets = secrets_res.json()["secrets"]
    # get the secret names from the secrets response and the secret names from the .env.secret file
    secret_env_file = DotEnv(f".env{'.dev' if dev else''}.secret").dict()
    secret_ids = {
        secret["name"]: secret["secret_id"]
        for secret in secrets
        if secret["name"] in secret_env_file.keys()
    }

    for key, value in secret_env_file.items():
        if not key in secret_ids:
            res = _call_griptape_cloud(
                host,
                "post",
                "/api/secrets",
                api_key,
                data={"name": key, "value": value},
            )
            res.raise_for_status()
            secret_ids[key] = res.json()["secret_id"]
        else:
            res = _call_griptape_cloud(
                host,
                "patch",
                f"/api/secrets/{secret_ids[key]}",
                api_key,
                data={"value": value},
            )
            res.raise_for_status()

    # now open the env file as a dict
    env_file = DotEnv(f".env{'.dev'if dev else ''}").dict()
    env_vars = []
    for key, value in env_file.items():
        env_vars.append({"name": key, "value": value})
    for key, value in secret_ids.items():
        env_vars.append({"name": key, "value": value, "source": "secret_ref"})

    # now that all secrets are created, update the structure env_vars with the secret IDs
    _call_griptape_cloud(
        host,
        "patch",
        f"/api/structures/{structure_id}",
        api_key,
        data={"env_vars": env_vars},
    )

    log(c, "Deployed environment to griptape cloud")


@task
def setup_branches(c):
    """Create branches for dev and prod"""
    # check if the dev branch exists
    dev_branch = (
        c.run("git branch --list origin/griptape_cloud_dev -r", hide=True)
        .stdout.strip()
        .split("/")[-1]
    )
    # branches on remote
    if not dev_branch:
        log(c, "Creating dev branch")
        c.run(
            f"git push origin $(git branch --show-current):griptape_cloud_dev --force",
            pty=True,
        )
    # check if the prod branch exists
    prod_branch = (
        c.run("git branch --list origin/griptape_cloud_dev -r", hide=True)
        .stdout.strip()
        .split("/")[-1]
    )
    if not prod_branch:
        log(c, "Creating prod branch")
        c.run(
            f"git push origin $(git branch --show-current):griptape_cloud --force",
            pty=True,
        )

    log(c, "Branches setup")


@task
def install(c):
    """Install dependencies"""
    c.run(
        "poetry lock && poetry install && poetry export --without-hashes -o requirements.txt",
        pty=True,
    )

    log(c, "Installed dependencies")


@task
def format(c):
    """Format code"""
    c.run("poetry run black .", pty=True)

    log(c, "Formatted code")


def _call_griptape_cloud(host, method, path, api_key, data=None):
    res = requests.request(
        method,
        f"{host}{path}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        data=json.dumps(data) if data else None,
    )
    res.raise_for_status()
    return res
