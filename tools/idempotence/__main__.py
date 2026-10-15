"""``python -X utf8 -m tools.idempotence <command>``

* ``build-corpus``  freeze the live READMEs of clones into ``data/idempotence/corpus.json``
* ``report``        the retention table for sealed regeneration bundles (``report.py``)
* ``gate``          the fixed-point gate over the corpus (``gate.py``); ``--mutations`` adds the
                    mutation sweep; the exit status is 1 when any README fails
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.idempotence import corpus, gate, report


def _build(args: argparse.Namespace) -> int:
    document = corpus.build(args.root, args.registry, args.captured)
    corpus.write(document, args.out)
    print(f"wrote {args.out} ({len(document['rows'])} repositories)")
    return 0


def _report(args: argparse.Namespace) -> int:
    entries = corpus.load(args.corpus) if args.corpus.is_file() else None
    bundles = report.discover(args.paths, entries, args.clones, args.exclude, args.since)
    rows = report.measure_all(bundles)
    text = report.render_table(rows)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    if args.json:
        args.json.write_text(
            json.dumps(report.rows_json(rows), indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


def _gate(args: argparse.Namespace) -> int:
    entries = corpus.load(args.corpus)
    chosen = [e for r, e in entries.items() if not args.repo or args.repo in r]
    rows = gate.gate(chosen, cold=args.cold)
    sys.stdout.write(gate.render_gate(rows))
    failed = [r for r in rows if not r.ok]
    if args.mutations:
        swept = gate.mutation_sweep(chosen)
        sys.stdout.write("\n" + gate.render_mutations(swept))
        failed += [r for r in swept if not r.ok]  # type: ignore[misc]
    return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.idempotence", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-corpus", help="freeze clones' READMEs into the corpus file")
    build.add_argument("--root", type=Path, action="append", required=True)
    build.add_argument("--registry", type=Path, default=corpus.DEFAULT_REGISTRY)
    build.add_argument("--out", type=Path, default=corpus.DEFAULT_CORPUS)
    build.add_argument("--captured", required=True, help="capture date, YYYY-MM-DD")
    build.set_defaults(run=_build)

    table = sub.add_parser("report", help="retention table for sealed bundles")
    table.add_argument("paths", type=Path, nargs="+", help="bundle dirs, candidates/ or checkouts")
    table.add_argument("--corpus", type=Path, default=corpus.DEFAULT_CORPUS)
    table.add_argument("--clones", type=Path, action="append", default=[], help="git history")
    table.add_argument("--exclude", type=Path, action="append", default=[], help="skip these")
    table.add_argument("--since", help="only bundles made at or after YYYY-MM-DDTHH:MM:SSZ")
    table.add_argument("--out", type=Path)
    table.add_argument("--json", type=Path)
    table.set_defaults(run=_report)

    check = sub.add_parser("gate", help="fixed-point gate over the corpus")
    check.add_argument("--corpus", type=Path, default=corpus.DEFAULT_CORPUS)
    check.add_argument("--repo", help="only repositories whose name contains this")
    check.add_argument("--mutations", action="store_true", help="also run the mutation sweep")
    check.add_argument("--cold", action="store_true", help="also prove two cold runs agree")
    check.set_defaults(run=_gate)

    args = parser.parse_args(argv)
    return int(args.run(args))


if __name__ == "__main__":
    raise SystemExit(main())
