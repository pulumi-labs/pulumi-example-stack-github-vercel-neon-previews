# Maintaining the PR preview example

- Preserve the single repository/PR stack boundary and six-resource ownership.
- Use the generated AnyTF Neon SDK, not the unrelated PyPI pulumi-neon beta.
- Read pinned provider source before changing schema fields or credential flow.
- Keep control-plane code on the trusted default branch. Never run head-branch
  code or dependency hooks in a job with management credentials.
- Stage only the reviewed application closure; reject symlinks and oversized files.
- Keep Vercel protection, per-preview bearer authentication and verified DB TLS.
- Preserve real locks and exact artifact evidence after approved VM resolution.
- Do not execute workloads, providers, SDKs or package managers on the workstation.
- Keep state, stack config, credentials and private logs out of source and exports.
- Private organization sources require an eligible existing Vercel Pro/Enterprise
  team. Do not work around plan rules through publication or mirrors.
- Workflow activation, account writes and publication require separate approval.
- Keep acceptance assets and acquisition records in the candidate run directory,
  outside the standalone runtime. Never claim unrun checks passed.
