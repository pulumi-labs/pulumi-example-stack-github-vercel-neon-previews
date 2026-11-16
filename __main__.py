"""Create only the resources owned by a single repository pull request."""

import hashlib
import hmac
import re
from pathlib import Path
from typing import Final

import pulumi
import pulumi_neon as neon
import pulumiverse_vercel as vercel

config = pulumi.Config()
MIN_TOKEN_SEED_BYTES: Final = 32
vercel_provider = vercel.Provider(
    "preview-vercel",
    team=pulumi.Config("vercel").require("team"),
)
repository = config.require("repository")
number = config.require_int("pullRequest")
commit = config.require("commitSha")
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
    message = "repository must be owner/repository"
    raise pulumi.RunError(message)
if number < 1 or not re.fullmatch(r"[0-9a-f]{40}", commit):
    message = "pullRequest must be positive and commitSha a full SHA"
    raise pulumi.RunError(message)
project_id = config.require("neonProjectId")
parent_id = config.require("parentBranchId")
scope = hashlib.sha256(repository.lower().encode()).hexdigest()[:12]
if pulumi.get_stack() != f"r-{scope}-pr-{number}":
    message = "Select the stack scoped to this repository and PR"
    raise pulumi.RunError(message)
preview_id = f"{scope}-pr-{number}"
name = f"notes-{preview_id}"


def preview_token(seed: str) -> str:
    """Derive a token usable only for this repository and PR."""
    if len(seed) < MIN_TOKEN_SEED_BYTES:
        message = "apiTokenSeed needs at least 32 random characters"
        raise pulumi.RunError(message)
    return hmac.new(seed.encode(), preview_id.encode(), hashlib.sha256).hexdigest()


token = config.require_secret("apiTokenSeed").apply(preview_token)
branch = neon.Branch(
    "preview-branch",
    project_id=project_id,
    parent_id=parent_id,
    name=name,
    protected="no",
    opts=pulumi.ResourceOptions(replace_on_changes=["projectId", "parentId"]),
)
endpoint = neon.Endpoint(
    "preview-compute",
    project_id=project_id,
    branch_id=branch.id,
    type="read_write",
    compute_provisioner="k8s-neonvm",
    autoscaling_limit_min_cu=0.25,
    autoscaling_limit_max_cu=0.25,
    suspend_timeout_seconds=300,
)
role = neon.Role(
    "preview-role",
    project_id=project_id,
    branch_id=branch.id,
    name=f"notes_{scope}_pr_{number}",
    opts=pulumi.ResourceOptions(additional_secret_outputs=["password"]),
)
database = neon.Database(
    "preview-database",
    project_id=project_id,
    branch_id=branch.id,
    name=f"notes_pr_{number}",
    owner_name=role.name,
)

# No Git integration: only this stack creates deployments. A project per PR also
# scopes aliases, build history, runtime secrets and final deletion to that PR.
project = vercel.Project(
    "preview-project",
    name=name,
    public_source=False,
    directory_listing=False,
    vercel_authentication=vercel.ProjectVercelAuthenticationArgs(
        deployment_type="standard_protection_new",
    ),
    opts=pulumi.ResourceOptions(provider=vercel_provider),
)
source = Path("upload")
if not source.is_dir():
    message = "Stage the reviewed app into upload/ before preview/update"
    raise pulumi.RunError(message)
files = vercel.get_project_directory(
    path=str(source),
    opts=pulumi.InvokeOptions(provider=vercel_provider),
)
deployment = vercel.Deployment(
    "preview-deployment",
    project_id=project.id,
    files=files.files,
    path_prefix=str(source),
    production=False,
    delete_on_destroy=True,
    environment={
        "PGHOST": endpoint.host_pooling,
        "PGPORT": "5432",
        "PGDATABASE": database.name,
        "PGUSER": role.name,
        "PGPASSWORD": pulumi.Output.secret(role.password),
        "PGSSLMODE": "verify-full",
        "PREVIEW_TOKEN": token,
        "PREVIEW_ID": preview_id,
        "COMMIT_SHA": commit,
    },
    meta={"repository": repository, "pullRequest": str(number), "commit": commit},
    opts=pulumi.ResourceOptions(
        provider=vercel_provider,
        depends_on=[database],
        additional_secret_outputs=["environment"],
    ),
)

pulumi.export("deploymentUrl", deployment.url)
pulumi.export("deploymentId", deployment.id)
pulumi.export("vercelProjectId", project.id)
pulumi.export("neonBranchId", branch.id)
pulumi.export("neonEndpointId", endpoint.id)
pulumi.export("previewId", preview_id)
pulumi.export("previewToken", token)
