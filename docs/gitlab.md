# GitLab CLI and explicit Pi skill

`packages.<system>.badwater-gitlab` / `pkgs.badwater-gitlab` supplies a skill-only
Pi package plus `bin/glab`, a symlink to the same system's pinned nixpkgs GLab.
`pkgs.piPackages.badwater-gitlab` is the normal named package descriptor.
There is no startup extension, private Pi copy, runtime installer or MCP proxy.
The CLI version comes from the consumer's nixpkgs; generated
`references/cli.md` records its exact version/path. Standalone owner and consumer
nixpkgs can differ, so check the actual installed help rather than latest docs.

```text
/skill:badwater-gitlab connect
/skill:badwater-gitlab review <approved project and issue/MR>
/skill:badwater-gitlab ci <approved project and pipeline/job>
```

The skill is explicit-only and read-first. Its small linked references cover
[authorization](../pkgs/badwater-gitlab/references/connection.md),
[CLI use](../pkgs/badwater-gitlab/references/cli.md),
[review](../pkgs/badwater-gitlab/references/review.md), and
[CI/data handling](../pkgs/badwater-gitlab/references/ci.md).
Installation is not permission for login, GitLab reads or writes. No swarm child
receives new tools or credentials by implication.

Home Manager/MCP declarations belong to badwater-ai. It registers GitLab's native
HTTP endpoint through Pi's existing sole builtin MCP owner, disabled by default.
MCP OAuth and GLab CLI authentication are separate private runtime operations.
A full CLI is not a read-only sandbox; GitLab account/token permissions remain
the access boundary. Do not copy a CLI token into MCP configuration.

`checks.<system>.badwater-gitlab` loads the installed package through the real
Pi SDK and checks skill discovery plus the managed CLI's version/command help
in an inert home. It performs no login or provider call. Consumer checks add
policy and native HTTP fixtures; they do not certify a live GitLab instance.
