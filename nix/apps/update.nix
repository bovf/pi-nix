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

        github_release() {
          local repo="$1" token="''${GITHUB_TOKEN:-}"
          [ -n "$token" ] || token="''${GH_TOKEN:-}"
          if [ -n "$token" ]; then
            curl -fsSL -H "Authorization: Bearer $token" "https://api.github.com/repos/$repo/releases/latest"
          else
            curl -fsSL "https://api.github.com/repos/$repo/releases/latest" || {
              echo "GitHub release lookup failed; set GITHUB_TOKEN or GH_TOKEN if rate-limited." >&2
              return 1
            }
          fi
        }

        resolve_build_hash() {
          local attr="$1" file="$2" field="$3" out code got
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
          python3 - "$attr" "$file" "$field" "$got" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, file, field, got = sys.argv[1:5]
        path = Path(file)
        text = path.read_text()
        body = r'(?:(?!^  [A-Za-z0-9_-]+ = ).)*?'
        pattern = rf'(^  {re.escape(attr)} = {body}{re.escape(field)} = )[^;]+(;)'
        text, count = re.subn(
            pattern,
            lambda m: f'{m.group(1)}"{got}"{m.group(2)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        if count != 1:
            raise SystemExit(f"expected one {field} substitution for {attr}, got {count}")
        path.write_text(text)
        PY
          nix build ".#$attr" --no-link
        }

        update_pi_core() {
          local release version source_url source_hash
          release=$(github_release "earendil-works/pi")
          version=$(echo "$release" | jq -er '.tag_name | sub("^v"; "")')
          source_url="https://github.com/earendil-works/pi/releases/download/v$version/pi-$version-source.tar.gz"
          source_hash=$(nix store prefetch-file --json "$source_url" | jq -er .hash)
          python3 - "$version" "$source_hash" <<'PY'
        import re
        import sys
        from pathlib import Path

        version, source_hash = sys.argv[1:3]
        path = Path("overlays/pi-coding-agent/default.nix")
        text = path.read_text()
        text, version_count = re.subn(r'(version = ")[^"]+(";)', rf'\g<1>{version}\2', text, count=1)
        text, source_count = re.subn(r'(src = .*?hash = ")[^"]+(";)', rf'\g<1>{source_hash}\2', text, count=1, flags=re.S)
        text, npm_count = re.subn(r'(npmDepsHash = )[^;]+(;)', r'\g<1>prev.lib.fakeHash\2', text, count=1)
        if (version_count, source_count, npm_count) != (1, 1, 1):
            raise SystemExit(f"unexpected Pi substitutions: {(version_count, source_count, npm_count)}")
        path.write_text(text)
        PY
          resolve_build_hash "pi-coding-agent" "overlays/pi-coding-agent/default.nix" "npmDepsHash"
        }

        update_ponytail() {
          local release version
          release=$(github_release "DietrichGebert/ponytail")
          version=$(echo "$release" | jq -er '.tag_name | sub("^v"; "")')
          python3 - "$version" <<'PY'
        import re
        import sys
        from pathlib import Path

        version = sys.argv[1]
        path = Path("overlays/pi-packages/default.nix")
        text = path.read_text()
        body = r'(?:(?!^  [A-Za-z0-9_-]+ = ).)*?'
        pattern = rf'(^  ponytail = {body}version = ")[^"]+(";{body}tag = ")[^"]+(";{body}hash = )[^;]+(;)'
        text, count = re.subn(
            pattern,
            lambda m: f'{m.group(1)}{version}{m.group(2)}v{version}{m.group(3)}prev.lib.fakeHash{m.group(4)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        if count != 1:
            raise SystemExit(f"expected one ponytail substitution, got {count}")
        path.write_text(text)
        PY
          resolve_build_hash "ponytail" "overlays/pi-packages/default.nix" "hash"
        }

        fill_missing_integrities() {
          local lock="$1" tmp key resolved archive integrity
          tmp=$(mktemp -d)
          while IFS=$'\t' read -r key resolved; do
            archive="$tmp/package.tgz"
            curl -fsSL "$resolved" -o "$archive"
            integrity=$(nix hash file --type sha512 --sri "$archive")
            jq --arg key "$key" --arg integrity "$integrity" \
              '.packages[$key].integrity = $integrity' "$lock" > "$lock.new"
            mv "$lock.new" "$lock"
          done < <(jq -r '
            .packages | to_entries[]
            | select(.key != "" and (.value.link // false | not)
              and .value.integrity == null
              and ((.value.resolved // "") | startswith("https://registry.npmjs.org/")))
            | [.key, .value.resolved] | @tsv
          ' "$lock")
          rm -rf "$tmp"
        }

        update_simple_npm() {
          local attr="$1" npm_name="$2" file="$3"
          local meta latest integrity tarball
          meta=$(npm_meta "$npm_name")
          latest=$(echo "$meta" | jq -er '."dist-tags".latest')
          integrity=$(echo "$meta" | jq -er --arg v "$latest" '.versions[$v].dist.integrity')
          tarball=$(echo "$meta" | jq -er --arg v "$latest" '.versions[$v].dist.tarball')
          [[ "$integrity" == sha512-* && "$tarball" == https://registry.npmjs.org/* ]] || {
            echo "Invalid npm metadata for $npm_name $latest" >&2
            exit 1
          }
          python3 - "$attr" "$latest" "$integrity" "$tarball" "$file" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, version, integrity, tarball, file = sys.argv[1:6]
        path = Path(file)
        text = path.read_text()
        body = r'(?:(?!^  [A-Za-z0-9_-]+ = ).)*?'
        pattern = rf'({re.escape(attr)} = {body}version = ")[^"]+(";{body}url = ")[^"]+(";{body}hash = ")[^"]+(";)'
        text, count = re.subn(
            pattern,
            lambda m: f'{m.group(1)}{version}{m.group(2)}{tarball}{m.group(3)}{integrity}{m.group(4)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        if count != 1:
            raise SystemExit(f"expected one substitution for {attr}, got {count}")
        path.write_text(text)
        PY
        }

        update_pi_package() {
          local attr="$1" npm_name="$2" lock_dir="$3" package_filter="''${4:-.}"
          local encoded meta latest integrity tarball tmp
          encoded="$npm_name"
          if [[ "$npm_name" == @*/* ]]; then
            encoded="''${npm_name/\//%2f}"
          fi
          meta=$(npm_meta "$encoded")
          latest=$(echo "$meta" | jq -er '."dist-tags".latest')
          integrity=$(echo "$meta" | jq -er --arg v "$latest" '.versions[$v].dist.integrity')
          tarball=$(echo "$meta" | jq -er --arg v "$latest" '.versions[$v].dist.tarball')
          [[ "$integrity" == sha512-* && "$tarball" == https://registry.npmjs.org/* ]] || {
            echo "Invalid npm metadata for $npm_name $latest" >&2
            exit 1
          }

          tmp=$(mktemp -d)
          curl -fsSL "$tarball" | tar -xz -C "$tmp"
          jq "$package_filter" "$tmp/package/package.json" > "$tmp/package/package.json.nix"
          mv "$tmp/package/package.json.nix" "$tmp/package/package.json"
          (cd "$tmp/package" && npm install --package-lock-only --ignore-scripts --omit=dev --legacy-peer-deps >/dev/null)
          fill_missing_integrities "$tmp/package/package-lock.json"
          cp "$tmp/package/package-lock.json" "$lock_dir/package-lock.json"
          rm -rf "$tmp"

          python3 - "$attr" "$latest" "$integrity" <<'PY'
        import re
        import sys
        from pathlib import Path

        attr, version, integrity = sys.argv[1:4]
        path = Path("overlays/pi-packages/default.nix")
        text = path.read_text()
        body = r'(?:(?!^  [A-Za-z0-9_-]+ = ).)*?'
        pattern = rf'(^  {re.escape(attr)} = {body}version = ")[^"]+(";{body}hash = ")[^"]+(";{body}npmDepsHash = )[^;]+(;)'
        text, count = re.subn(
            pattern,
            lambda m: f'{m.group(1)}{version}{m.group(2)}{integrity}{m.group(3)}prev.lib.fakeHash{m.group(4)}',
            text,
            count=1,
            flags=re.S | re.M,
        )
        if count != 1:
            raise SystemExit(f"expected one substitution for {attr}, got {count}")
        path.write_text(text)
        PY

          resolve_build_hash "$attr" "overlays/pi-packages/default.nix" "npmDepsHash"
        }

        update_pi_core
        update_simple_npm "pi-vim" "pi-vim" "overlays/pi-vim/default.nix"
        update_pi_package "rpiv-todo" "@juicesharp/rpiv-todo" "pkgs/rpiv-todo"
        update_pi_package "pi-archimedes" "pi-archimedes" "pkgs/pi-archimedes"
        update_pi_package "pi-subagents" "pi-subagents" "pkgs/pi-subagents"
        update_pi_package "remote-pi" "remote-pi" "pkgs/remote-pi" "del(.devDependencies)"
        update_pi_package "plannotator-pi-extension" "@plannotator/pi-extension" "pkgs/pi-extension"
        update_pi_package "pi-wait-what" "@narumitw/pi-wait-what" "pkgs/pi-wait-what" "del(.devDependencies, .peerDependencies)"
        update_pi_package "pi-lsp" "@narumitw/pi-lsp" "pkgs/pi-lsp" "del(.devDependencies, .peerDependencies)"
        update_pi_package "pi-chrome-devtools" "@narumitw/pi-chrome-devtools" "pkgs/pi-chrome-devtools" "del(.devDependencies, .peerDependencies)"
        update_pi_package "pi-btw" "@narumitw/pi-btw" "pkgs/pi-btw" "del(.devDependencies, .peerDependencies)"
        update_pi_package "pi-goal" "@narumitw/pi-goal" "pkgs/pi-goal" "del(.devDependencies, .peerDependencies)"
        update_ponytail

        nix build .#pi-coding-agent .#pi-vim .#pi-search .#pi-search-mcp .#hunk-review .#rpiv-todo .#pi-archimedes .#pi-subagents .#remote-pi .#plannotator-pi-extension .#ponytail .#pi-wait-what .#pi-lsp .#pi-chrome-devtools .#pi-btw .#pi-goal --no-link
        nix run .#fmt
      '';
    };
  in {
    type = "app";
    program = nixpkgs.lib.getExe update;
  };
}
