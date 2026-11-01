# Managed GitLab CLI

Nix supplies **glab @GLAB_VERSION@** at `@GLAB@`; the package's `bin/glab` links
to this exact executable. No `npx`, npm/pip installer, self-update or global
GitLab settings writer is used. The nixpkgs wrapper disables update checks and
telemetry by default. Preserve existing personal authentication and preferences.

Only after separate CLI/network approval, set `HOST`, `PROJECT` and `IID` to the
operator-approved instance, project and identifier. For example:

```sh
GITLAB_HOST="$HOST" glab mr view "$IID" --repo "$PROJECT"
GITLAB_HOST="$HOST" glab mr diff "$IID" --repo "$PROJECT"
GITLAB_HOST="$HOST" glab issue view "$IID" --repo "$PROJECT"
GITLAB_HOST="$HOST" glab ci status --repo "$PROJECT"
```

Check the pinned command's `--help` for supported flags before documenting or
running it. Repository inference/default hosts can select another instance;
stop on a host/project mismatch. Do not export a global host or change Git SSH
configuration merely to run one approved request. Pagination/limits matter.

Generic API/shell access is not a safe substitute for a missing MCP read tool.
Do not run mutation commands, `auth token`, raw debug traces or credential-file
inspection. `auth status` can contact the instance: it is not an offline probe.
A full CLI can do more than this read-first skill permits; GitLab credentials
and user approval, not this document, enforce actual account privileges.

Official [CLI reference](https://docs.gitlab.com/cli/) and
[configuration](https://docs.gitlab.com/cli/configuration/).
