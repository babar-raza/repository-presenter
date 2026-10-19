"""``python -m tools.lane_r_audit <command>``: pin, measure, baseline, corpus, ratchet.

* ``pin [--control REV]``       write data/lane_r_corpus/pins.json from the control revision
* ``measure``                   print every metric as JSON (deterministic)
* ``baseline``                  write data/lane_r_corpus/ledger_baseline_v2.json
* ``corpus build|check|report`` write, verify, or measure the labeled corpus (cases, split)
* ``ratchet write``             record the current metrics as the ratchet (improvements only)
* ``control-rerun``             re-run today's deterministic checks over the 30 pinned bundles
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import measure as measure_module
from .pinned import PINS_PATH, PinnedInputError, build_pins, load_pins

CONTROL_REVISION = "4a7baf11926a6ee8707f41b8c6a525367c5f8fcd"


def _ratchet() -> int:
    from . import ratchet

    values = ratchet.current_values()
    waivers: list[dict[str, object]] = []
    if ratchet.RATCHET_PATH.exists():
        previous = ratchet.load()
        waivers = list(previous.get("waivers", []))
        problems = ratchet.regressions(
            ratchet.flatten(previous["metrics"]), ratchet.flatten(values), waivers
        )
        if problems:
            for line in problems:
                print(f"REGRESSION: {line}", file=sys.stderr)
            return 1
    text = measure_module.dumps(ratchet.document(values, waivers, load_pins().control_revision))
    ratchet.RATCHET_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {ratchet.RATCHET_PATH}")
    return 0


def _corpus(action: str) -> int:
    from . import build_corpus, corpus_report
    from .corpus import CORPUS_DIR

    if action == "report":
        sys.stdout.write(measure_module.dumps(corpus_report.report_all()))
        return 0
    files = build_corpus.documents(build_corpus.build_all())
    if action == "build":
        build_corpus.write(CORPUS_DIR, files)
        print(f"wrote {len(files)} corpus files under {CORPUS_DIR}")
        return 0
    diffs = build_corpus.differences(CORPUS_DIR, files)
    for line in diffs:
        print(line, file=sys.stderr)
    return 1 if diffs else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.lane_r_audit")
    sub = parser.add_subparsers(dest="command", required=True)
    pin = sub.add_parser("pin")
    pin.add_argument("--control", default=CONTROL_REVISION)
    sub.add_parser("measure")
    sub.add_parser("baseline")
    corpus_cmd = sub.add_parser("corpus")
    corpus_cmd.add_argument("action", choices=("build", "check", "report"))
    ratchet_cmd = sub.add_parser("ratchet")
    ratchet_cmd.add_argument("action", choices=("write",))
    sub.add_parser("control-rerun")
    args = parser.parse_args(argv)
    try:
        if args.command == "pin":
            text = measure_module.dumps(build_pins(args.control).to_json())
            PINS_PATH.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {PINS_PATH}")
        elif args.command == "measure":
            sys.stdout.write(measure_module.dumps(measure_module.measure()))
        elif args.command == "corpus":
            return _corpus(args.action)
        elif args.command == "ratchet":
            return _ratchet()
        elif args.command == "control-rerun":
            from . import control_rerun

            text = measure_module.dumps(control_rerun.rerun_all())
            (Path(measure_module.BASELINE_V2_PATH).parent / "control_rerun.json").write_text(
                text, encoding="utf-8", newline="\n"
            )
            print("wrote data/lane_r_corpus/control_rerun.json")
        else:
            measured = measure_module.measure()
            text = measure_module.dumps(measure_module.baseline_v2(measured))
            Path(measure_module.BASELINE_V2_PATH).write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {measure_module.BASELINE_V2_PATH}")
    except PinnedInputError as exc:
        print(f"PINNED INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
