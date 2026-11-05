"""Calculate strict/tolerant diagnostics without inference or modifying the source."""

import argparse
import hashlib
import json
from pathlib import Path

from partner_copilot.evaluation.abstention import abstention_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve() or args.output.exists():
        parser.error("Choose a new output file, different from source")
    data = args.source.read_bytes()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if len({r["experiment_id"] for r in rows}) != 1:
        parser.error("Mixed experiments")
    result = {
        "source": args.source.name,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        **abstention_report(rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: view["metrics"] for name, view in result["views"].items()}, indent=2))


if __name__ == "__main__":
    main()
