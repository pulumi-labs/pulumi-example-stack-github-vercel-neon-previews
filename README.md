# GitHub PR previews with Vercel and Neon

Give reviewers an authenticated Python notes API and an independent PostgreSQL
branch for each same-repository pull request. Python Pulumi wires the branch's
generated credentials into its Vercel deployment. Updating a PR replaces the
deployment while keeping its notes. Closing or merging the PR destroys its
deployment, Vercel project, database, role, compute endpoint and branch.

**Validation, November 16, 2026: live preview deployment, branch isolation and
PR-close cleanup are UNRUN.** Installed Vercel and generated Neon SDK contracts,
complete dependency locks, native syntax, strict lint and type checks passed in
an approved disposable VM. The real notes ASGI application rejected missing and
wrong tokens with HTTP 401 and oversized input with HTTP 422, without a database
connection. These component checks do not prove Vercel deployment or SQL storage.
Provider accounts, plan eligibility and workflow activation remain unresolved.
Keep Actions disabled during private quality review.

Private review repository: `pulumi-labs/pulumi-example-stack-github-vercel-neon-previews`.

```sh
git clone https://github.com/pulumi-labs/pulumi-example-stack-github-vercel-neon-previews.git
cd pulumi-example-stack-github-vercel-neon-previews
```

## What it owns

An existing Neon project and a synthetic baseline branch remain operator-owned.
Each PR owns four Neon resources (`Branch`, `Endpoint`, `Role`, `Database`) and
two Vercel resources (`Project`, `Deployment`). A fresh role and fresh database
are created on the child branch, so the application never receives the baseline
role's password or a cloud management token. The project has Vercel Standard
Protection plus an application bearer token specific to the repository and PR.

The GitHub workflow is the event integration. It runs trusted default-branch
infrastructure, reads the current PR through the GitHub API, copies only three
application files from the immutable head SHA, and uploads them through the
native Vercel provider. It never imports, installs or executes PR code on the
controller. Vercel builds the application with only that PR's runtime secrets.
No Vercel Git integration is connected, avoiding duplicate automatic deployments.

Stack names are `r-<repository-sha256-prefix>-pr-<number>` in the
`pr-previews-github-vercel-neon` project. The repository prefix is the first
12 hexadecimal characters of SHA-256 over lowercase `owner/repository`.
Resource names use the same prefix. Keep the repository identity and Pulumi
organization fixed throughout an active preview's lifetime.

## Supported inputs and provider caveat

Use Python 3.12, Pulumi CLI and Python SDK 3.273.0, `pulumiverse-vercel` 5.26.1,
and AnyTF `terraform-provider` 1.0.1 wrapping `kislerdm/neon` 0.18.0.
The Neon SDK must be generated from these exact parameters; the unrelated
PyPI `pulumi-neon` 0.0.1b1 only supports a project resource and is unsuitable.
Do not install that package in place of the generated SDK.

The selected Neon Terraform provider is now archived. Its versioned source and
Pulumi registry schema support the branch, pooled host, role password and database
operations used here. The newer official `neondatabase/neon` 0.19.0 beta changes
the schema and exposes role credentials as Terraform ephemeral resources.
It is not a drop-in replacement for the managed `Role.password` output used here.
Migration requires a reviewed credential path and renewed native validation.
The pinned provider's delete code treats HTTP 422 as absence; independently
verify actual branch/endpoint deletion rather than trusting destroy alone.

## Accounts, plans and credentials

Keep the example repository private for review. **Vercel Hobby cannot deploy
from a private GitHub organization repository.** For the intended private
organization source, require access to an already-authorized Pro or Enterprise
team and verify its eligibility before activation. File upload is used for
lifecycle ownership, not as a policy exception. Do not publish, mirror, transfer
the source or start a paid subscription to bypass this restriction. If no eligible
existing team is available, deployment is blocked.

The operator also needs a Neon account with capacity for a child branch and a
0.25 CU read/write endpoint per active PR, and a Pulumi backend with durable
encrypted state. Neon free-plan quotas may suffice for a small trial but must
be checked against the actual account, parent branches, storage and current
compute quota. There is no requirement for Kubernetes, AWS, a new runner platform
or a new subscription. GitHub-hosted private-repository Actions minutes may
also be metered. The project cap is $50 total per UTC calendar week; compute
limits and scale-to-zero are not spending caps.

This workflow uses GitHub environment secrets and branch restrictions. A private
organization repository therefore also needs an existing GitHub Team or
Enterprise plan; verify that capability rather than assuming GitHub Free
provides private environments. No new plan purchase is authorized.

Create the GitHub environment `preview-control` only after activation approval.
Restrict its deployments to the default branch and restrict who may change the
default branch, workflow, environment and secrets. Configure:

| Kind | Name | Scope |
| --- | --- | --- |
| Secret | `PULUMI_ACCESS_TOKEN` | Backend identity allowed to create/update/destroy this example's preview stacks; backend state contains encrypted DB passwords and API tokens. |
| Secret | `NEON_API_KEY` | Dedicated organization/project management key able to create/read/delete branches, endpoints, roles, databases and retrieve role passwords in the disposable project. Do not use a production-wide key. |
| Secret | `VERCEL_API_TOKEN` | Token scoped to the eligible preview team with project/deployment read, create, update and delete access. It can affect other projects in that team; use a dedicated team where available. |
| Secret | `PREVIEW_TOKEN_SEED` | At least 32 random characters. Used only by trusted infrastructure to derive separate API tokens. Never supplied to the app. |
| Variable | `PULUMI_ORG` | Backend organization or personal account namespace. |
| Variable | `NEON_PROJECT_ID` | Existing disposable-data project. |
| Variable | `NEON_PARENT_BRANCH_ID` | Existing synthetic baseline branch. Never production or customer data. |
| Variable | `VERCEL_TEAM` | Exact eligible team ID or slug, verified by the operator. |

`GITHUB_TOKEN` has only contents/read and pull-requests/read. No PAT, repository
write, webhook secret, PR comment or GitHub provider is needed. No credentials
belong in source, logs, command arguments, PR comments or committed stack config.
Vercel and Neon control tokens exist only during reconciliation. App runtime
receives PG connection fields, its own role password, its API token, preview ID
and commit SHA. Neon database connections use `verify-full` with Python's
system CA file; a runtime without a CA file fails rather than disabling TLS checks.

Forks and PRs targeting non-default branches are rejected before secrets are
used. Same-repository application authors are trusted with their own synthetic
preview data and token: they can change application code that runs in Vercel.
They cannot receive the management tokens through this mechanism. Protect
workflow and environment administration as a separate trust boundary.

## Prepare in the approved execution environment

These commands are for an approved, scanned execution environment, never the
workstation. First acquire and scan the exact CLI, provider binaries, action
closures, generated SDK and dependency wheels listed in the internal acquisition
record. The checked-in infrastructure lock and application requirements contain
complete resolver-generated package pins and hashes for Python 3.12. Private
resolver-path comments are omitted. Newly generated SDK wheels remain separate
artifacts: inspect, hash and scan them before installation. Dependency changes
must respect the four-day release policy.

From a standalone copy of this directory:

```sh
uv venv --python 3.12.10
pulumi package gen-sdk terraform-provider@1.0.1 \
  --language python --out sdks/neon --local -- \
  registry.opentofu.org/kislerdm/neon 0.18.0
uv pip install --python .venv/bin/python \
  --require-hashes -r requirements.lock
uv pip install --python .venv/bin/python \
  --require-hashes -r build-requirements.lock
# Use reviewed packaging backends, then scan the generated wheel before install.
uv build sdks/neon/python --wheel --no-build-isolation \
  --python .venv/bin/python --out-dir sdk-wheels
uv pip install --python .venv/bin/python --no-deps sdk-wheels/*.whl
PREVIEW_APP_SOURCE=app .venv/bin/python stage_app.py
```

For the first native review, check the generated `pulumi_neon.Branch`,
`Endpoint`, `Role`, `Database` signatures, `host_pooling` and secret `password`
outputs, actual provider serialization and file upload metadata. Generate the
SDK wheel with reviewed setuptools 80.9.0 and wheel 0.45.1, hash and scan it before
installation, and preserve its source and provenance. Infrastructure locks do
not license or clear an independently generated artifact.
Review Vercel's managed build/runtime acquisition and scan boundary
with the parent; this example does not claim control over Vercel's service image.

Set the management credentials securely in the process environment or secret
store. Select the repository-scoped stack and configure it:

```sh
scope=$(printf '%s' "${REPOSITORY,,}" | sha256sum | cut -c1-12)
stack="$PULUMI_ORG/pr-previews-github-vercel-neon/r-$scope-pr-$PR_NUMBER"
pulumi stack select "$stack" --create
pulumi config set repository "$REPOSITORY"
pulumi config set pullRequest "$PR_NUMBER"
pulumi config set commitSha "$HEAD_SHA"
pulumi config set neonProjectId "$NEON_PROJECT_ID"
pulumi config set parentBranchId "$NEON_PARENT_BRANCH_ID"
pulumi config set vercel:team "$VERCEL_TEAM"
printf '%s' "$PREVIEW_TOKEN_SEED" | pulumi config set apiTokenSeed --secret
pulumi preview --refresh --diff
```

Review the actual plan and account targets before `pulumi up`. The plan must
contain only the six PR resources and provider/stack bookkeeping. Parent project
and branch must never appear as managed create/delete resources. Never change
the branch parent or project casually: they force branch replacement and data loss.

## Activate and use

After the exact source, dependency locks, scans, native preview and account plan
have passed their gates, the operator may separately authorize installation of
`.github/workflows/previews.yml` in the private standalone repository's default
branch. It handles opened, synchronized, reopened and closed same-repo PRs.
Manual dispatch accepts a PR number and reconciles its live state, including
missed close events. Do not enable this workflow during publication review.

Each run checks live GitHub state rather than trusting an old event. Per-PR
concurrency never cancels an in-flight update; a queued run reads the latest
state. It checks for a close again after the build and destroys immediately if
needed. A close queued after that check will perform cleanup. Empty stack state
is retained after destroy for idempotent repeated close events and reopening.
Reopening creates a fresh branch and loses the old notes, as intended.

Get `deploymentUrl` from the selected stack. Vercel may return a hostname;
prefix it with `https://` if necessary. Standard Protection requires a signed-in
team member or an operator-managed automation bypass. A bypass, if used, is a
separate secret in the HTTP client; do not disable deployment protection just to
make a smoke test pass. Obtain `previewToken` through a secure secret-output
channel, never a public log or PR comment. Send:

```sh
curl --fail-with-body "$PREVIEW_URL/api/notes" \
  -H "Authorization: Bearer $PREVIEW_TOKEN"
curl --fail-with-body "$PREVIEW_URL/api/notes" \
  -H "Authorization: Bearer $PREVIEW_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"body":"reviewed in preview A"}'
```

Successful POST returns a UUID, note body and timestamp with HTTP 201. GET
returns the latest hundred notes plus preview ID and commit SHA. Empty/overlong
bodies fail with 422; missing/wrong bearer tokens fail with 401 after passing
Vercel's separate protection layer. Compare two PRs: a note written in A must
not exist in B; using A's bearer token against B must fail.

## Cleanup and recovery

Closing a PR, merged or unmerged, runs `pulumi destroy --refresh` for its exact
stack. `delete_on_destroy=True` is essential: Vercel retains deployments by
default. The dependency graph removes the deployment before its database/role/
compute/branch and before its Vercel project. No shared project or baseline
branch is destroyed. Old deployments are deleted on replacement.

If a job fails, times out, is disabled or loses credentials, cleanup is not
guaranteed. Keep encrypted state and re-dispatch that PR after repairing access.
For urgent manual cleanup, use the trusted source and the same scoped stack:

```sh
pulumi stack select "$stack"
pulumi destroy --refresh --yes
```

Independently query Neon for the recorded branch and endpoint IDs and Vercel for
the deployment and project IDs. Confirm provider-specific NotFound responses,
and list the corresponding scoped resource names to detect partial-create
orphans. Do not classify authentication failures or Neon HTTP 422 as proof of
absence. Keep shared resources, and retain state until inventory proves cleanup.
Only then remove empty stack history if desired. API seed/token rotation replaces
deployments; it does not reset the DB unless the branch itself is replaced.

This is a small preview example, not a production migration system, an automatic
production deploy, or a tenant-security boundary for untrusted organization
members. Database content is deliberately disposable. An unavailable close
workflow requires operator recovery; no scheduler or automatic paid cleanup
service is installed.

## References and maintenance

- [Pulumi Any Terraform Provider](https://www.pulumi.com/docs/iac/concepts/providers/any-terraform-provider/)
- [Neon 0.18.0 Pulumi schema](https://www.pulumi.com/registry/packages/neon/schema.json)
- [Versioned Neon provider source](https://github.com/kislerdm/terraform-provider-neon/tree/v0.18.0)
- [Versioned Vercel Python SDK](https://github.com/pulumiverse/pulumi-vercel/tree/v5.26.1/sdk/python/pulumiverse_vercel)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel private repository plan rules](https://vercel.com/docs/git#deploying-private-git-repositories)
- [GitHub pull_request_target security model](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target)
- [GitHub environment plan availability](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [Official Neon provider migration](https://github.com/neondatabase/terraform-provider-neon)

The community Neon provider is MPL-2.0; Pulumiverse Vercel is Apache-2.0. This
example contains authored application and infrastructure source, not copied
provider implementation. Authored-code licensing and a maintenance owner remain
to be selected before any public release. Report problems through the reviewed
repository's issue tracker once one exists; no public repository is asserted.
