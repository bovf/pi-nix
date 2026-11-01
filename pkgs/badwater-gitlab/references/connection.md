# Connection: the human grants access

## Check prerequisites without probing the private instance

Ask the operator for the GitLab version and whether the instance permits its
native MCP server. Current official endpoint: `https://<host>/api/v4/mcp`.
Older versions/settings may not support it. No live compatibility claim is made
by package installation or an offline fixture. Stop if unavailable; do not
install a third-party proxy or invent `glab mcp serve` as a fallback.

## Pi MCP authorization

1. After the approved Home Manager switch, restart Pi. `/mcp` lists
   `badwater-gitlab` as disabled; it makes no connection in that state.
2. The human chooses Enable, optionally **Enable in this project** for a trusted
   project, then Sign in (or `/mcp login badwater-gitlab`) and reviews GitLab's
   browser authorization. Never do this automatically or request a token in chat.
3. Current GitLab MCP requires MCP-scoped OAuth or a supported fine-grained token;
   an ordinary CLI token or working Git SSH key is not MCP authorization.
4. Verify status and only a named, authorized read operation. Unknown/mutating
   tools remain hidden. OAuth success is not permission for every operation.

Pi stores/refreshes MCP credentials privately in `~/.pi/agent/mcp-auth.json`.
Do not read it. `/mcp` Sign out or `/mcp logout badwater-gitlab` removes that
client authorization; revoke it in GitLab as needed. Heavy and Spy sign in
separately. TLS verification remains enabled; no new LAN firewall port is needed.

The global entry defaults to disabled on each managed switch. A trusted project
Enable override persists separately; keep personal `.pi/mcp.json` out of commits.
Alternatively the human may explicitly opt into declarative `gitlab.mcp.connect`.
Neither project enablement nor the hostname restricts API access to that project:
use least-privileged GitLab account/token permissions for a real access boundary.

## CLI login is separate

The human may run the managed `glab auth login --hostname <host>` after approving
CLI access. Self-managed OAuth needs a public-client application/client ID; web
and supported device flows are described in the official authentication guide.
Verify actual pinned `auth login --help`; do not assume latest-doc flags exist.
Prefer the OS keyring. If unavailable, stop and agree on private storage rather
than silently accepting plaintext. Never use tokens in argv, Git/Nix declarations,
shared environment files or model-visible output. Do not reconfigure the existing
Git credential helper or overwrite personal glab settings as part of installation.

Sources: [GitLab MCP](https://docs.gitlab.com/user/model_context_protocol/mcp_server/),
[CLI authentication](https://docs.gitlab.com/cli/authentication/).
