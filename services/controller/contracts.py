"""Validate wire DTOs with the existing v1 bundle, without duplicated model fields."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = json.loads((ROOT / "contracts/v1/bundle.json").read_text(encoding="utf-8"))
FORMAT_CHECKER = FormatChecker()
if FORMAT_CHECKER.conforms("not-a-timestamp", "date-time"):
    raise RuntimeError("date-time checker unavailable: install requirements.txt (rfc3339-validator).")

VALIDATORS = {
    name: Draft202012Validator(
        {"$ref": f"#/$defs/{name}", "$defs": BUNDLE["$defs"]},
        format_checker=FORMAT_CHECKER,
    )
    for name in BUNDLE["$defs"]
}


class DemoError(Exception):
    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def validate(name, value):
    try:
        VALIDATORS[name].validate(value)
    except ValidationError as exc:
        location = ".".join(str(x) for x in exc.absolute_path) or "body"
        # Do not echo a possibly sensitive submitted value in the error response.
        raise DemoError(422, "INVALID_SCHEMA", f"{name}: invalid {location}") from exc
