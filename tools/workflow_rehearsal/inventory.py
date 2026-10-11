"""Workflow inventory: what every hosted workflow needs, generated from the YAML itself.

TC-REF-10-01. Parses ``.github/workflows/*.yml`` and renders one deterministic Markdown block:
triggers, permissions, environments, variables, secrets, job graph, artifacts and concurrency. The
block is embedded in ``docs/OPERATIONS_RUNBOOK.md`` between two marker comments; ``--check`` fails
when the committed block differs from what the YAML says now, so the runbook cannot drift from the
workflows. Nothing here talks to a network, GitHub, or a provider.

Run: ``python tools/workflow_rehearsal/inventory.py [--write | --check] [--runbook PATH]``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
RUNBOOK = REPO_ROOT / "docs" / "OPERATIONS_RUNBOOK.md"
BEGIN = "<!-- BEGIN GENERATED: workflow-inventory (python tools/workflow_rehearsal/inventory.py --write) -->"
END = "<!-- END GENERATED: workflow-inventory -->"

_VARS = re.compile(r"\bvars\.([A-Za-z_][A-Za-z0-9_]*)")
_SECRETS = re.compile(r"\bsecrets\.([A-Za-z_][A-Za-z0-9_]*)")
_ENV_NAMES = re.compile(r"\b(REPOSITORY_PRESENTER_[A-Z0-9_]+)\b")
_EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.S)


def load_workflow(path: Path) -> dict[str, Any]:
    """Parse one workflow; PyYAML reads the bare key ``on`` as boolean ``True`` (YAML 1.1)."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} is not a YAML mapping")
    if True in loaded and "on" not in loaded:
        loaded["on"] = loaded.pop(True)
    return loaded


def _scalar_or_list(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in sorted(value.items(), key=lambda kv: str(kv[0])))
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def triggers(workflow: dict[str, Any]) -> list[str]:
    """One line per trigger, with its schedule, inputs, or types."""
    on = workflow.get("on")
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return [str(t) for t in on]
    lines: list[str] = []
    for name, config in sorted((on or {}).items(), key=lambda kv: str(kv[0])):
        config = config or {}
        if name == "schedule":
            lines.extend(f"schedule `{item['cron']}` (UTC)" for item in config)
        elif name in ("workflow_dispatch", "workflow_call"):
            inputs = config.get("inputs") or {}
            parts = []
            for key, spec in sorted(inputs.items()):
                spec = spec or {}
                flag = "required" if spec.get("required") else (
                    f"default {spec['default']!r}" if spec.get("default") is not None else "optional"
                )
                parts.append(f"{key} ({spec.get('type', 'string')}, {flag})")
            secrets = sorted((config.get("secrets") or {}) if name == "workflow_call" else [])
            suffix = f"; secrets: {', '.join(secrets)}" if secrets else ""
            lines.append(f"{name}" + (f" inputs: {'; '.join(parts)}" if parts else "") + suffix)
        elif name == "repository_dispatch":
            lines.append(f"repository_dispatch types: {_scalar_or_list(config.get('types'))}")
        else:
            detail = _scalar_or_list(config) if config else ""
            lines.append(f"{name}" + (f" ({detail})" if detail != "-" and detail else ""))
    return lines


def _uses(job: dict[str, Any]) -> list[str]:
    found = [str(step["uses"]) for step in job.get("steps") or [] if "uses" in step]
    if "uses" in job:
        found.append(str(job["uses"]))
    return found


def _app_token_scopes(job: dict[str, Any]) -> list[str]:
    """The ``permission-*`` and ``repositories`` narrowing of each App installation token step."""
    scopes = []
    for step in job.get("steps") or []:
        if str(step.get("uses", "")).startswith("actions/create-github-app-token"):
            with_ = step.get("with") or {}
            perms = sorted(k for k in with_ if str(k).startswith("permission-"))
            scopes.append("+".join(f"{k}={with_[k]}" for k in perms) or "(all App permissions)")
    return scopes


def _artifacts(job: dict[str, Any]) -> list[str]:
    out = []
    for step in job.get("steps") or []:
        uses = str(step.get("uses", ""))
        name = (step.get("with") or {}).get("name") or (step.get("with") or {}).get("pattern")
        if uses.startswith("actions/upload-artifact"):
            out.append(f"up:{name}")
        elif uses.startswith("actions/download-artifact"):
            out.append(f"down:{name}")
    return out


def describe(path: Path) -> dict[str, Any]:
    """Everything the inventory states about one workflow, as plain data."""
    text = path.read_text(encoding="utf-8")
    expressions = _EXPRESSION.findall(text)
    workflow = load_workflow(path)
    jobs = workflow.get("jobs") or {}
    job_rows = []
    for job_id, job in jobs.items():
        needs = job.get("needs") or []
        needs = [needs] if isinstance(needs, str) else list(needs)
        env = job.get("environment")
        if isinstance(env, dict):
            env = env.get("name")
        job_rows.append(
            {
                "id": job_id,
                "needs": needs,
                "if": job.get("if"),
                "runs_on": job.get("runs-on", "(reusable call)" if "uses" in job else "-"),
                "permissions": job.get("permissions"),
                "environment": env,
                "concurrency": job.get("concurrency"),
                "matrix": bool((job.get("strategy") or {}).get("matrix")),
                "timeout": job.get("timeout-minutes"),
                "uses": _uses(job),
                "app_token_scopes": _app_token_scopes(job),
                "artifacts": _artifacts(job),
            }
        )
    return {
        "file": path.name,
        "name": workflow.get("name", path.stem),
        "triggers": triggers(workflow),
        "permissions": workflow.get("permissions"),
        "concurrency": workflow.get("concurrency"),
        "jobs": job_rows,
        "variables": sorted({v for e in expressions for v in _VARS.findall(e)}),
        "secrets": sorted({v for e in expressions for v in _SECRETS.findall(e)}),
        "inherits_secrets": bool(re.search(r"^\s*secrets:\s*inherit\b", text, re.M)),
        "env_names": sorted(set(_ENV_NAMES.findall(text))),
    }


def inventory(directory: Path = WORKFLOWS_DIR) -> list[dict[str, Any]]:
    return [describe(p) for p in sorted(directory.glob("*.yml"))]


def _perm(value: Any) -> str:
    if value is None:
        return "(inherits)"
    if value == {}:
        return "none"
    if isinstance(value, str):
        return value
    return ", ".join(f"{k}: {v}" for k, v in sorted(value.items()))


def _code(items: list[str]) -> str:
    return ", ".join(f"`{i}`" for i in items) if items else "-"


def render(rows: list[dict[str, Any]]) -> str:
    """The Markdown block, deterministic for a given YAML tree."""
    out: list[str] = []
    out.append("#### Summary\n")
    out.append("| Workflow | File | Triggers | Workflow permissions | Concurrency |")
    out.append("|---|---|---|---|---|")
    for r in rows:
        conc = "-" if not r["concurrency"] else _scalar_or_list(r["concurrency"]).replace("|", "/")
        trig = "<br>".join(t.replace("|", "/") for t in r["triggers"])
        out.append(f"| {r['name']} | `{r['file']}` | {trig} | {_perm(r['permissions'])} | {conc} |")
    out.append("")
    out.append("#### Variables, secrets and environment switches")
    out.append("")
    out.append("| File | Repository variables (`vars.*`) | Secrets (`secrets.*`) | Switch names in scripts |")
    out.append("|---|---|---|---|")
    for r in rows:
        secrets = _code(r["secrets"]) + (" + `secrets: inherit`" if r["inherits_secrets"] else "")
        out.append(f"| `{r['file']}` | {_code(r['variables'])} | {secrets} | {_code(r['env_names'])} |")
    out.append("")
    for r in rows:
        out.append(f"#### `{r['file']}` job graph")
        out.append("")
        out.append("| Job | Needs | Runs on | Effective permissions | App token scope | Environment | Concurrency | Matrix | Condition |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for j in r["jobs"]:
            cond = "-" if not j["if"] else "`" + " ".join(str(j["if"]).split()).replace("|", "/") + "`"
            conc = "-" if not j["concurrency"] else _scalar_or_list(j["concurrency"]).replace("|", "/")
            out.append(
                f"| `{j['id']}` | {_code(j['needs'])} | {j['runs_on']} "
                f"| {_perm(j['permissions'] if j['permissions'] is not None else r['permissions'])}"
                f"{'' if j['permissions'] is not None else ' (workflow)'} "
                f"| {'; '.join(j['app_token_scopes']) or '-'} | {j['environment'] or '-'} | {conc} | {'yes' if j['matrix'] else '-'} | {cond} |"
            )
        arts = sorted({a for j in r["jobs"] for a in j["artifacts"]})
        if arts:
            out.append("")
            out.append(f"Artifacts: {_code(arts)}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def splice(runbook_text: str, block: str) -> str:
    """Replace the generated block of ``runbook_text``; ValueError when the markers are absent."""
    start = runbook_text.find(BEGIN)
    end = runbook_text.find(END)
    if start < 0 or end < start:
        raise ValueError("the runbook has no workflow-inventory markers")
    return runbook_text[: start + len(BEGIN)] + "\n\n" + block + "\n" + runbook_text[end:]


def generated_block(runbook_text: str) -> str:
    start = runbook_text.find(BEGIN)
    end = runbook_text.find(END)
    if start < 0 or end < start:
        raise ValueError("the runbook has no workflow-inventory markers")
    return runbook_text[start + len(BEGIN) : end].strip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runbook", type=Path, default=RUNBOOK)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="splice the block into the runbook")
    mode.add_argument("--check", action="store_true", help="fail when the runbook block is stale")
    args = parser.parse_args(argv)
    block = render(inventory())
    if args.write:
        args.runbook.write_text(splice(args.runbook.read_text(encoding="utf-8"), block), encoding="utf-8", newline="\n")
        return 0
    if args.check:
        if generated_block(args.runbook.read_text(encoding="utf-8")).strip() != block.strip():
            print(f"{args.runbook}: generated inventory block is stale; run with --write", file=sys.stderr)
            return 1
        return 0
    sys.stdout.write(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
