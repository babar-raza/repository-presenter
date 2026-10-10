# reseal_wave - local parallel reseal runner (TC-RSL-01)

Owner/reviewer operator tooling (see `tools/README.md`): never imported by `src/`, never read by a
gate, not a governed change. It runs the README transaction for many repositories at once, each in
its own isolated work clone, and reports one row per repository. Follows
`plans/healing/r1-reseal-operations.md`: it never forces a seal past a review rejection, never edits
a disposition or plan, and never retries hoping for a different roll.

## What it does, per repository

1. A **plain clone** of the control repo, not a `git worktree` (Go examples fail inside a worktree
   with "error obtaining VCS status"): `git clone --shared --no-checkout <main checkout>
   E:\rp\<family>-<platform>`, `git checkout --detach <cut sha>`, `git remote remove origin`
   (nothing run there can push), and the main checkout's `.venv` linked in as a junction. Short
   paths (`--clone-root`, default `E:\rp`) because of Windows MAX_PATH. `scripts/new_worktree.sh`
   stays a development tool.
2. Subprocess environment only: `PYTHONPATH=<clone>/src`; `D:\Program Files\nodejs` prepended to
   `PATH` (npm then resolves; the machine's PATH is never edited); `RP_TOOLCHAIN_REGISTRY` set to
   `--toolchain-registry` (default: the private registry copy that adds the `vcvarsall` key, when it
   exists, so Cells-Cpp's install command can resolve through the MSVC fallback; the shared
   `D:\tools\rp-toolchains\TOOLCHAIN_PATHS.txt` is not edited); `PYTHONUTF8=1`,
   `PYTHONUNBUFFERED=1`. The interpreter is the main checkout's `.venv` python (3.13.2, the
   environment of record), never the bare `python` on PATH. The runner checks that
   `repository_presenter` imports from the clone's `src`.
3. `repository-presenter preflight` once, then `present --repo <r> --invocation-record inv-1.json`,
   then a second `present` in a fresh process (`inv-2.json`, the adoption / no-op run), then
   `verify-noop-proof --first inv-1.json --second inv-2.json`. Logs and records are in
   `<clone>/runs/reseal-logs/` (`preflight|present-1|present-2|noop` `.out`/`.err`).
4. A run over `--timeout-minutes` (default 45, covering all phases) has its process tree killed
   and is recorded `TIMEOUT`.

It never edits `project/state.yaml`, never commits or pushes, never writes the main checkout's
`candidates/`, and never touches GitHub (the clone uses `GH_TOKEN` read-only). Whatever a run
produced (a bundle under `<clone>/candidates/`, a handoff under `evidence/`) stays in its clone;
the row's `changed_paths` lists it so the supervisor can stage bundles into wave PRs.

## Usage

Needs the gateway variables in the environment (`GPT_OSS_ENDPOINT`, `GPT_OSS_API_KEY`; checked by
name, never printed) and GitHub read access (`GH_TOKEN`, or `--gh-token-from-gh` to take it from
`gh auth token` into the subprocess environment only). Run it with the main checkout's venv python:

```
.venv/Scripts/python.exe tools/reviewer/reseal_wave/reseal_wave.py --dry-run          # plan only
.venv/Scripts/python.exe tools/reviewer/reseal_wave/reseal_wave.py --gh-token-from-gh \
    --max-parallel 3                                                                  # all enabled
.venv/Scripts/python.exe tools/reviewer/reseal_wave/reseal_wave.py --gh-token-from-gh \
    --repo aspose-words-foss/Aspose.Words-FOSS-for-Python --family slides --platform net
```

| flag | meaning |
|---|---|
| `--clone-root DIR` | parent of the work clones, default `E:\rp` |
| `--toolchain-registry FILE` | exported as `RP_TOOLCHAIN_REGISTRY` to every run |
| `--cut REF` | cut ref or sha, default `origin/main` (fetched, then pinned to its full sha; registry read from the cut) |
| `--repo`, `--family`, `--platform` | narrow the enabled entries (`mode != disabled`, `active`); an unknown or disabled `--repo` is an error |
| `--max-parallel N` | default 3; more than 8 is refused. Preflight probed 525/525 HTTP 200 up to 8 concurrent, which is only liveness weight: widen after a clean first wave |
| `--timeout-minutes M` | per repository, default 45 |
| `--results-dir DIR` | default `<main checkout>/runs/reseal/<cut8>/` (gitignored) |
| `--retry-failed` | re-queue repositories whose last row is `FAILED`, `TIMEOUT` or `NOT_READY` (fresh clone `<f>-<p>-2`) |
| `--dry-run` | print the plan (clone path, skips); start nothing |
| `--python`, `--extra-path` | override the venv python and the PATH directories prepended |

**Resume:** rerun the same command. Repositories whose `results.jsonl` already has a row are skipped
(`--retry-failed` re-queues failed ones; `SEALED` is never re-queued). A Ctrl+C kills the running
children; repositories without a row simply rerun (on a fresh clone name, since the old clone is
kept as evidence).

## Result rows

`results.jsonl` is the append-only source (last row per repository wins); `results.csv` and
`results.json` are regenerated after every finished repository. Columns: `status`
(`SEALED`, `NOT_READY`, `NON_PROCESSABLE`, `FAILED`, `TIMEOUT`), exit codes per phase,
`stage_reached` (last `present` stage printed), `validation_pass/fail/pending`, `review_verdict`,
`review_findings`, `provider_calls_run1/run2` (counted from each invocation's own `calls.jsonl`
ledger), `minutes`, `bundle_state`, `bundle_path` (inside the clone), `noop_proof`
(`VERIFIED`, `NOT_APPLICABLE`, `FAILED:<reason>`, `NOT_RUN`), `failure_class` (a guess for triage:
`BC-xx` with `failure_stage`, `gateway`, `toolchain`, `clone`, `timeout`, `noop_proof`, `runner`,
`unknown`), `failure_detail`, `changed_paths`, `workdir`, `attempt`, `cut`.
`SEALED` means exit 0 twice, bundle `READY_FOR_PROPOSAL`, review `ACCEPT`, and a verified no-op proof.

## Secrets

The runner never prints or dumps the environment, and the child commands' logs are files in the
clone. `failure_detail` is passed through `redact()` (the value of every secret-shaped variable is
masked). Do not run `env`, `set`, `printenv` or list `Env:` while using it: the shell holds tokens.

## Cleanup

Clones are kept (they hold the bundles and logs). When a wave is staged and merged, remove a clone:
`rmdir E:\rp\<name>\.venv` first (a junction; never a recursive delete through it), then delete
`E:\rp\<name>`.

Tests for the pure parts (queue, limits, parsing, resume, redaction, clone creation) and a fake-CLI
orchestration test: `tests/test_reseal_wave.py`.
