#!/usr/bin/env python3
"""Validates every fixture flow against schema/flow/v0.yaml.

This is not a linter: it checks only the document shape, so that the
fixtures stay usable as a conformance suite while the spec evolves.
Requires: pip install pyyaml jsonschema
"""
import pathlib
import sys

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
schema = yaml.safe_load((ROOT / "schema/flow/v0.yaml").read_text())
jsonschema.Draft202012Validator.check_schema(schema)
validator = jsonschema.Draft202012Validator(schema)

failed = False
for flow_path in sorted((ROOT / "fixtures").rglob("*.flow.yaml")):
    expected = yaml.safe_load((flow_path.parent / "expected.yaml").read_text())
    expects_schema_violation = any(
        f["rule"] == "flow/structure/schema-violation" for f in expected["findings"]
    )
    errors = list(validator.iter_errors(yaml.safe_load(flow_path.read_text())))
    rel = flow_path.relative_to(ROOT)
    if errors and not expects_schema_violation:
        failed = True
        print(f"FAIL {rel}")
        for error in errors:
            print(f"     {'/'.join(map(str, error.absolute_path))}: {error.message}")
    elif not errors and expects_schema_violation:
        failed = True
        print(f"FAIL {rel}: expected a schema violation, document is valid")
    else:
        print(f"ok   {rel}")

sys.exit(1 if failed else 0)
