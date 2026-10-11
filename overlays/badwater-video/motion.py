"""Bounded native EffectCraft caption/effect recipes. No expressions or arbitrary scripts."""

from fractions import Fraction
from native import NativeMCP
from store import atomic_json, digest, rational, publish


def groups(words, maximum=4):
    result = []
    for word in words:
        if (
            not result
            or len(result[-1]) >= maximum
            or rational(word["at"]) - rational(result[-1][-1]["end"]) > Fraction(2, 5)
            or result[-1][-1]["text"].rstrip().endswith((".", "?", "!"))
        ):
            result.append([])
        result[-1].append(word)
    return result


def render(engine, p, work, val, style):
    executable = engine.config.get("craftApplications", {}).get("effectcraft")
    if not executable:
        raise ValueError(
            "animated captions/effects require selected EffectCraft native backend"
        )
    settings = val["output"]
    fps = rational(settings["fps"])
    word_groups = groups(val["captionWords"])
    cues = val["effects"]
    result = []
    # Windowed comps bound layer trees, native protocol and transparent intermediates.
    active = [(rational(g[0]["at"]), rational(g[-1]["end"]), g) for g in word_groups]
    intervals = [(a, b) for a, b, _ in active] + [
        (rational(c["at"]), rational(c["at"]) + rational(c["duration"])) for c in cues
    ]
    if not intervals:
        return []
    windows = []
    for a, b in sorted(intervals):
        if (
            windows
            and a <= windows[-1][1] + Fraction(1, 2)
            and b - windows[-1][0] <= 30
        ):
            windows[-1] = (windows[-1][0], max(windows[-1][1], b))
        else:
            windows.append((a, b))
    for index, (begin, end) in enumerate(windows):
        # Snap to output frames; caption word mapping remains exact in provenance.
        begin = Fraction(int(begin * fps), 1) / fps
        end = Fraction(-(-end * fps // 1), 1) / fps
        duration = end - begin
        if duration <= 0 or duration > 30:
            raise ValueError("effect overlay windows must fit 30 seconds")
        folder = engine.policy.write(work / f"effect-{index}" / "overlay.mov").parent
        argv = [executable, "mcp"]
        with (
            (folder / "native.stderr").open("w") as log,
            NativeMCP(
                engine.policy.sandbox(argv, folder),
                log,
                timeout=engine.config.get("timeoutSeconds", 1200),
            ) as fx,
        ):
            fx.tool("open_project", {"new": True})

            def command(name, params):
                return fx.tool("execute_command", {"command": name, "params": params})

            comp = command(
                "comp.new",
                {
                    "name": f"Overlay-{index}",
                    "width": settings["width"],
                    "height": settings["height"],
                    "frameRate": float(fps),
                    "duration": float(duration),
                },
            )["comp"]
            count = 0
            size = style.get("size", max(12, settings["height"] // 24))
            normal = style.get("color", "#ffffff")
            highlight = style.get("highlight", "#ffcc00")
            anchor = style.get("anchor", "bottom")
            if anchor not in {"top", "middle", "bottom"}:
                raise ValueError("caption anchor must be top/middle/bottom")
            y = (
                settings["height"]
                * {"top": 0.18, "middle": 0.5, "bottom": 0.78}[anchor]
            )

            def text_layer(text, start, stop, x, y, color, pop=False):
                nonlocal count
                count += 1
                if count > 260:
                    raise ValueError(
                        "native text layer budget exceeded; use shorter caption phrases/windows"
                    )
                layer = command(
                    "layer.newText",
                    {
                        "text": text,
                        "name": f"text-{count}",
                        "size": size,
                        "fill": color,
                        "stroke": "#000000",
                        "applyStroke": True,
                        "strokeWidth": max(1, size / 16),
                        "position": [x, y],
                        "justify": "center",
                    },
                )["layer"]
                command(
                    "layer.timing",
                    {
                        "layers": [layer],
                        "start": float(start),
                        "in": float(start),
                        "out": float(stop),
                    },
                )
                if pop:
                    end_key = min(float(stop - start), 0.16)
                    fx.tool(
                        "add_keyframe",
                        {
                            "layer": layer,
                            "path": "transform/scale",
                            "keys": [
                                {"time": 0, "value": [96, 96]},
                                {"time": end_key / 2, "value": [108, 108]},
                                {"time": end_key, "value": [100, 100]},
                            ],
                            "interpolation": "easyEase",
                        },
                    )
                return layer

            for a, b, group in active:
                if b <= begin or a >= end:
                    continue
                widths = [
                    max(size * 0.55, len(w["text"]) * size * 0.55) + size * 0.25
                    for w in group
                ]
                width = sum(widths)
                if width > settings["width"] * 0.85:
                    widths = [x * settings["width"] * 0.85 / width for x in widths]
                x = settings["width"] / 2 - sum(widths) / 2
                for w, width in zip(group, widths):
                    x += width / 2
                    lo = max(begin, rational(w["at"])) - begin
                    hi = min(end, rational(w["end"])) - begin
                    if hi <= lo:
                        x += width / 2
                        continue
                    mode = style.get("mode", "highlight")
                    if mode == "highlight":
                        text_layer(
                            w["text"],
                            max(a, begin) - begin,
                            min(b, end) - begin,
                            x,
                            y,
                            normal,
                        )
                        text_layer(w["text"], lo, hi, x, y, highlight, True)
                    else:
                        text_layer(
                            w["text"],
                            lo,
                            (min(b, end) - begin) if mode == "reveal" else hi,
                            x,
                            y,
                            highlight if w.get("emphasis") else normal,
                            True,
                        )
                    x += width / 2
            for cue in cues:
                a, b = (
                    rational(cue["at"]),
                    rational(cue["at"]) + rational(cue["duration"]),
                )
                if a < end and b > begin:
                    size = min(200, max(12, settings["height"] // 10))
                    text_layer(
                        cue["text"],
                        max(a, begin) - begin,
                        min(b, end) - begin,
                        settings["width"] / 2,
                        settings["height"] * 0.3,
                        highlight,
                        cue["recipe"] != "callout",
                    )
            native = folder / "overlay.ecproj"
            fx.tool("save_project", {"path": str(native)})
            before = fx.tool("get_comp", {"comp": comp})
            fx.tool("open_project", {"path": str(native)})
            after = fx.tool("get_comp", {"comp": comp})
            if before != after:
                raise ValueError(
                    "native EffectCraft layers/keyframes differ after save/reopen"
                )
            movie = folder / "overlay.mov"
            command(
                "renderQueue.add",
                {
                    "comp": comp,
                    "format": "prores",
                    "proresProfile": "4444",
                    "channels": "rgba",
                    "output": str(movie),
                    "audio": "off",
                },
            )
            report = command("renderQueue.render", {"wait": True})
            if not report.get("items") or any(
                x.get("status") != "Done" for x in report["items"]
            ):
                raise ValueError("native EffectCraft overlay render did not complete")
        if not movie.is_file() or movie.stat().st_size > engine.config.get(
            "maxEffectAssetBytes", 1024 * 1024 * 1024
        ):
            raise ValueError("effect asset missing or exceeds its configured bound")
        content_hash = digest(movie)
        target = engine.policy.write(p.root / "derived" / content_hash / "overlay.mov")
        if target.exists():
            if digest(target) != content_hash:
                raise ValueError("content-addressed effect asset was modified")
        else:
            publish(movie, target)
        data = {
            "path": str(target),
            "hash": content_hash,
            "at": str(begin),
            "duration": str(duration),
            "nativeProject": str(native),
            "nativeProjectHash": digest(native),
            "layers": count,
            "backend": executable,
            "alpha": "native ProRes 4444 RGBA; downstream composite verified by native QC",
        }
        atomic_json(folder / "provenance.json", data)
        result.append(data)
    return result
