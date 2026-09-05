# Lane B decision log (append-only; entries in RESEARCH_AND_GUIDELINES.md section 31 shape; the owner merges)

Lane: `lane-b` (project/lanes/lane-b.yaml). Prompt: project/loop-prompt-lane-b.md.

- **2026-09-06 · LANE-B-00 · the lane's Rust toolchain lives under `C:\tools\rp-toolchains\rustup`,
  not `runs/toolchains/`.** `RUSTUP_HOME` is `...\rustup\rustup-home`, `CARGO_HOME` is
  `...\rustup\cargo-home`, cargo is called by absolute path, and `rustup-init` ran
  `-y --profile minimal --no-modify-path --default-toolchain stable`, so no PATH or profile changed.
  Alternative rejected: `runs/toolchains/`, as G4-W16's parenthetical says. Evidence: `runs/` is
  gitignored disposable run state, so any clean re-downloads the toolchain inside W16's 2-hour box,
  and OWNER-06's GCC/Ninja already sit under `C:\tools\rp-toolchains` with `TOOLCHAIN_PATHS.txt` as
  the machine's toolchain registry; LANE-B-00's text (2026-09-06) names this root and is the later of
  the two. Reversal: repoint both variables at `runs/toolchains/` and re-run `rustup-init`; only the
  LANE-B-00 receipt records the path.
- **2026-09-06 · LANE-B-00 · OWNER-06's resume predicate is reproduced independently, not taken on
  trust.** The owner marked it `SATISFIED` in `state.yaml` at 81a10ac on the reviewer session's own
  probe; LANE-B-00 rebuilt the probe from scratch — `cmake 4.4.1 -G Ninja` configuring, building and
  running C++20 with `g++.exe` 16.2.0 and `ninja` 1.13.2 from `TOOLCHAIN_PATHS.txt`, three steps at
  exit 0, the binary printing `cxx202002 total=12`. Alternative rejected: read the file's `verified`
  line and move on. Evidence: LANE-B-00's own text says "verify", and a probe that uses
  `std::integral` and `std::views::filter` makes C++20 a compile requirement, not a claim. Reversal:
  none needed; G4-W13's remaining wait is G4-W10 and G4-W09.
- **2026-09-06 · LANE-B-00 · `pytest -n auto` is nondeterministic on a developer machine that has
  real `GPT_OSS_*` credentials, and the hosted matrix is the honest verdict.** Six local runs of the
  same tree gave 503 passed; 501 passed + 2 errors; 500 passed + 3 errors + 1 failed; 500 passed +
  2 errors — a *different* subset of `tests/test_cli.py` each time, every one an LLM output
  rejection at fixture setup ("output rejected twice ... fact format:output.glb is UNRESOLVED"),
  never an assertion about this item. Diagnosis: `GPT_OSS_ENDPOINT` and `GPT_OSS_API_KEY` are set in
  this machine's process environment, so those fixtures compose against the real gateway; `ci.yml`
  sets neither, so hosted CI takes the deterministic path and PR #1 passed 3.11, 3.12 and 3.13.
  Alternative rejected: repair the fixtures — the cause is in `composition/` or `prompts/`, which
  the lane must never edit, and this item adds no Python. Reversal: the primary loop owns it; a
  cheap fix would be to unset both variables for the suite, or gate those fixtures on the fake
  gateway, so the local run measures the code rather than the model. Control: with both variables
  unset the suite passed 503/503 first attempt, which is what identifies the gateway as the cause.
- **2026-09-06 · LANE-B-00 · the lane's `tsc` is warmed now, into a disposable npm profile under
  `C:\tools\rp-toolchains\npm`.** `npm_config_prefix` and `npm_config_cache` point there, so nothing
  lands in the user profile and no PATH is edited; G4-W14's verifier calls `tsc` by absolute path or
  `npx.cmd` against that prefix. Alternative rejected: let `npx typescript` download inside G4-W14's
  2-hour box. Evidence: RESEARCH section 28.12 point 6 says provision toolchains before the cohort
  item that needs them, never inside its box. Reversal: delete the directory; `npx typescript` still
  works, at the cost of a download in the box.
