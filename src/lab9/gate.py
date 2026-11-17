"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.eval import aggregate
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]

    def audit_report(report: dict, role: str) -> dict:
        errors = []
        manifest = report.get("manifest", {})
        rows, metrics = report.get("rows", []), report.get("metrics", {})
        seeds, items = manifest.get("seeds", []), manifest.get("items", 0)
        if report.get("evaluator_failures"):
            errors.append("evaluator_failures is nonempty")
        if not seeds or len(set(seeds)) != len(seeds) or items < 1:
            errors.append("invalid items/seeds in manifest")
        if spec.get("seeds") is not None and set(seeds) != set(spec["seeds"]):
            errors.append("manifest seeds differ from spec")
        if len(rows) != items * len(seeds):
            errors.append("row count differs from items x seeds")
        for name, value in metrics.items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                errors.append(f"metric {name} is missing/nonfinite")
        for m in spec["metrics"]:
            if m["id"] not in metrics:
                errors.append(f"missing aggregate metric {m['id']}")
        pairs, tags = [], {}
        for row in rows:
            pair = (row.get("item_id"), row.get("seed"))
            if not isinstance(pair[0], str) or pair[1] not in seeds:
                errors.append("invalid row item_id/seed")
            pairs.append(pair)
            slices = row.get("slices", [])
            if not isinstance(slices, list) or not all(isinstance(s, str) for s in slices):
                errors.append("invalid slice tags")
                slices = []
            tags[pair] = frozenset(slices)
            for metric in graded:
                value = row.get(metric)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value not in (0, 1):
                    errors.append(f"{pair}: {metric} is not a finite binary grader result")
            if "cost" in row and (not isinstance(row["cost"], (int, float))
                                  or not math.isfinite(row["cost"]) or row["cost"] < 0):
                errors.append(f"{pair}: invalid cost")
        unique = set(pairs)
        item_ids = {p[0] for p in unique}
        if len(unique) != len(pairs):
            errors.append("duplicate (item_id, seed) rows")
        if len(item_ids) != items or unique != {(item, seed) for item in item_ids for seed in seeds}:
            errors.append("incomplete item x seed coverage")
        for item in item_ids:
            if len({tags[p] for p in unique if p[0] == item}) > 1:
                errors.append(f"{item}: slice tags differ across seeds")
        if not errors:
            computed = aggregate([{**row, "cost": row.get("cost", 0.0)} for row in rows],
                                 graded, k_values=spec.get("pass_k", []))
            for name, value in computed.items():
                if name in metrics and value is not None and abs(value - metrics[name]) > 1e-8:
                    errors.append(f"aggregate {name} disagrees with row evidence")
        problems.extend(f"{role}: {error}" for error in errors)
        return tags

    pr_tags, base_tags = audit_report(pr, "PR"), audit_report(base, "baseline")
    if pr_tags.keys() != base_tags.keys():
        problems.append("PR and baseline have different (item_id, seed) sets")
    elif pr_tags != base_tags:
        problems.append("PR slice tags differ from baseline")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old_entries, new_entries, slice_rules=False):
            key = (lambda x: (x["name"], x["metric"])) if slice_rules else (lambda x: x["id"])
            current = {key(entry): entry for entry in new_entries}
            for old in old_entries:
                name = key(old)
                if name not in current:
                    problems.append(f"ratchet: removed {name}")
                    continue
                new = current[name]
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: disabled blocking for {name}")
                before, after = (old, new) if slice_rules else (old.get("threshold", {}), new.get("threshold", {}))
                for threshold in ("min", "max", "max_increase"):
                    if threshold in before:
                        value = after.get(threshold)
                        if (not isinstance(value, (int, float)) or not math.isfinite(value)
                            or (value < before[threshold] if threshold == "min" else value > before[threshold])):
                            problems.append(f"ratchet: loosened {name}/{threshold}")
                if before.get("no_significant_drop") and not after.get("no_significant_drop"):
                    problems.append(f"ratchet: removed no_significant_drop for {name}")
                for field in ("kind", "grader", "level"):
                    if field in old and new.get(field) != old[field]:
                        problems.append(f"ratchet: changed {name}/{field}")
        ratchet(base_spec.get("metrics", []), spec.get("metrics", []))
        ratchet(base_spec.get("slices", []), spec.get("slices", []), slice_rules=True)
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        note, failed = "", False
        if not a or a.keys() != b.keys() or not all(math.isfinite(v) for v in [*a.values(), *b.values()]):
            value, failed, note = None, True, "missing/nonfinite slice values or mismatched items"
        else:
            value = math.fsum(a.values()) / len(a)
            failed = "min" in entry and value < entry["min"]
            if entry.get("no_significant_drop"):
                keys = sorted(a)
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                failed = failed or hi < 0
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        if failed and entry.get("blocking"):
            blocked.append(sid)
        verdict = ("BLOCK" if entry.get("blocking") else "warn") if failed else "ok"
        lines.append(f"  {sid:<36} {value!s:<8} {note:<35} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", default=os.environ.get("EVAL_BASE_SPEC"),
                    help="metric spec on main, for the ratchet check (M7); defaults to EVAL_BASE_SPEC")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
