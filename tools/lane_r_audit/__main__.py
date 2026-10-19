"""``python -m tools.lane_r_audit <command>``: pin, measure, baseline.

* ``pin [--control REV]``       write data/lane_r_corpus/pins.json from the control revision
* ``measure``                   print every metric as JSON (deterministic)
* ``baseline``                  write data/lane_r_corpus/ledger_baseline_v2.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import measure as measure_module
from .pinned import PINS_PATH, PinnedInputError, build_pins

CONTROL_REVISION = "4a7baf11926a6ee8707f41b8c6a525367c5f8fcd"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.lane_r_audit")
    sub = parser.add_subparsers(dest="command", required=True)
    pin = sub.add_parser("pin")
    pin.add_argument("--control", default=CONTROL_REVISION)
    sub.add_parser("measure")
    sub.add_parser("baseline")
    args = parser.parse_args(argv)
    try:
        if args.command == "pin":
            text = measure_module.dumps(build_pins(args.control).to_json())
            PINS_PATH.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {PINS_PATH}")
        elif args.command == "measure":
            sys.stdout.write(measure_module.dumps(measure_module.measure()))
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
