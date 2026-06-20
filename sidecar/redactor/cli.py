from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze_file
from .exporter import export_redacted_file
from .serde import export_request_from_dict
from .validation import validate_material_submission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="redactor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--file", required=True)
    analyze_parser.add_argument("--file-id", required=True)
    analyze_parser.add_argument("--person-name", default="")
    analyze_parser.add_argument("--employer-term", action="append", default=[])
    analyze_parser.add_argument("--material-type", default="social", choices=["social", "other"])

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--request", required=True)

    export_json_parser = subparsers.add_parser("export-json")
    export_json_parser.add_argument("payload")

    validate_parser = subparsers.add_parser("validate-submission")
    validate_parser.add_argument("--material-type", required=True, choices=["social", "other"])
    validate_parser.add_argument("--file", action="append", default=[])

    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            analysis = analyze_file(
                args.file,
                file_id=args.file_id,
                person_name=args.person_name,
                employer_terms=args.employer_term,
                material_type=args.material_type,
            )
            print(json.dumps(analysis.to_dict(), ensure_ascii=False))
            return 0

        if args.command == "export":
            payload = json.loads(Path(args.request).read_text(encoding="utf-8"))
            output_path = export_redacted_file(export_request_from_dict(payload))
            print(json.dumps({"outputPath": output_path}, ensure_ascii=False))
            return 0

        if args.command == "export-json":
            payload = json.loads(args.payload)
            output_path = export_redacted_file(export_request_from_dict(payload))
            print(json.dumps({"outputPath": output_path}, ensure_ascii=False))
            return 0

        if args.command == "validate-submission":
            validate_material_submission(args.material_type, args.file)
            print(json.dumps({"ok": True}, ensure_ascii=False))
            return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
