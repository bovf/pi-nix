{nixpkgs}: {
  mkUpdateApp = system: let
    pkgs = nixpkgs.legacyPackages.${system};
    update = pkgs.writeShellApplication {
      name = "update";
      runtimeInputs = with pkgs; [curl jq nix nodejs python3 git];
      text = ''
        nix flake update

        npm_meta() {
          curl -fsSL "https://registry.npmjs.org/$1"
        }

        update_simple_npm() {
          local attr="$1" npm_name="$2" file="$3"
          local meta latest integrity tarball
          meta=$(npm_meta "$npm_name")
          latest=$(echo "$meta" | jq -r '."dist-tags".latest')
          integrity=$(echo "$meta" | jq -r --arg v "$latest" '.versions[$v].dist.integrity')
          tarball=$(echo "$meta" | jq -r --arg v "$latest" '.versions[$v].dist.tarball')
          python3 - "$attr" "$latest" "$integrity" "$tarball" "$file" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, version, integrity, tarball, file = sys.argv[1:6]
        path = Path(file)
        text = path.read_text()
        pattern = rf'({re.escape(attr)} = .*?version = ")[^"]+(";.*?url = ")[^"]+(";.*?hash = ")[^"]+(";)'
        text = re.sub(
            pattern,
            lambda m: f'{m.group(1)}{version}{m.group(2)}{tarball}{m.group(3)}{integrity}{m.group(4)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        path.write_text(text)
        PY
        }

        update_pi_package() {
          local attr="$1" npm_name="$2" lock_dir="$3" minimal_lock="''${4:-false}"
          local encoded meta latest integrity tarball tmp got out code
          encoded="$npm_name"
          if [[ "$npm_name" == @*/* ]]; then
            encoded="''${npm_name/\//%2f}"
          fi
          meta=$(npm_meta "$encoded")
          latest=$(echo "$meta" | jq -r '."dist-tags".latest')
          integrity=$(echo "$meta" | jq -r --arg v "$latest" '.versions[$v].dist.integrity')
          tarball=$(echo "$meta" | jq -r --arg v "$latest" '.versions[$v].dist.tarball')

          tmp=$(mktemp -d)
          curl -fsSL "$tarball" | tar -xz -C "$tmp"
          if [ "$minimal_lock" = true ]; then
            jq 'del(.devDependencies, .peerDependencies)' "$tmp/package/package.json" > "$tmp/package/package.json.nix"
            mv "$tmp/package/package.json.nix" "$tmp/package/package.json"
          fi
          (cd "$tmp/package" && npm install --package-lock-only --ignore-scripts --omit=dev --legacy-peer-deps >/dev/null)
          cp "$tmp/package/package-lock.json" "$lock_dir/package-lock.json"
          rm -rf "$tmp"

          python3 - "$attr" "$latest" "$integrity" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, version, integrity = sys.argv[1:4]
        path = Path("overlays/pi-packages/default.nix")
        text = path.read_text()
        pattern = rf'(^  {re.escape(attr)} = .*?version = ")[^"]+(";.*?hash = ")[^"]+(";.*?npmDepsHash = )[^;]+(;)'
        text = re.sub(
            pattern,
            lambda m: f'{m.group(1)}{version}{m.group(2)}{integrity}{m.group(3)}prev.lib.fakeHash{m.group(4)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        path.write_text(text)
        PY

          set +e
          out=$(nix build ".#$attr" --no-link 2>&1)
          code=$?
          set -e
          if [ "$code" -eq 0 ]; then
            return 0
          fi
          got=$(printf '%s\n' "$out" | sed -n 's/.*got:[[:space:]]*\(sha256-[^[:space:]]*\).*/\1/p' | tail -1)
          if [ -z "$got" ]; then
            printf '%s\n' "$out"
            exit "$code"
          fi
          python3 - "$attr" "$got" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, got = sys.argv[1:3]
        path = Path("overlays/pi-packages/default.nix")
        text = path.read_text()
        pattern = rf'(^  {re.escape(attr)} = .*?npmDepsHash = )[^;]+(;)'
        text = re.sub(
            pattern,
            lambda m: f'{m.group(1)}"{got}"{m.group(2)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        path.write_text(text)
        PY
          nix build ".#$attr" --no-link
        }

        update_simple_npm "pi-vim" "pi-vim" "overlays/pi-vim/default.nix"
        update_pi_package "rpiv-todo" "@juicesharp/rpiv-todo" "pkgs/rpiv-todo"
        update_pi_package "pi-archimedes" "pi-archimedes" "pkgs/pi-archimedes"
        update_pi_package "pi-subagents" "pi-subagents" "pkgs/pi-subagents"
        update_pi_package "plannotator-pi-extension" "@plannotator/pi-extension" "pkgs/pi-extension"
        update_pi_package "pi-wait-what" "@narumitw/pi-wait-what" "pkgs/pi-wait-what" true
        update_pi_package "pi-lsp" "@narumitw/pi-lsp" "pkgs/pi-lsp" true
        update_pi_package "pi-chrome-devtools" "@narumitw/pi-chrome-devtools" "pkgs/pi-chrome-devtools" true
        update_pi_package "pi-btw" "@narumitw/pi-btw" "pkgs/pi-btw" true
        update_pi_package "pi-goal" "@narumitw/pi-goal" "pkgs/pi-goal" true

        nix build .#pi-coding-agent .#pi-vim .#pi-search .#pi-search-mcp .#rpiv-todo .#pi-archimedes .#pi-subagents .#plannotator-pi-extension .#ponytail .#pi-wait-what .#pi-lsp .#pi-chrome-devtools .#pi-btw .#pi-goal --no-link
        nix run .#fmt
      '';
    };
  in {
    type = "app";
    program = nixpkgs.lib.getExe update;
  };
}
