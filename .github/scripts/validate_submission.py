#!/usr/bin/env python3
"""
Validate ARC Prize Community Leaderboard submission YAML files.

Usage:
    python validate_submission.py <path_to_submission.yaml> [...]

Exit codes:
    0 — all submissions valid
    1 — one or more validation errors
"""

import sys
import os
import re
from datetime import datetime

import yaml
import requests

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

REQUIRED_TOP_LEVEL = ["name", "authors", "description", "code_url", "versions"]
VALID_ARC_VERSIONS = {"arc-agi-1", "arc-agi-2", "arc-agi-3"}
OPTIONAL_URL_FIELDS = ["paper_url", "twitter_url"]
DIR_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
LINK_CHECK_TIMEOUT = 10  # seconds


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

class ValidationError:
    def __init__(self, field, message):
        self.field = field
        self.message = message

    def __str__(self):
        return f"  ✗ [{self.field}] {self.message}"


def check_url_resolves(url, field_name):
    """Check that a URL returns a non-error HTTP status."""
    errors = []
    try:
        resp = requests.head(url, timeout=LINK_CHECK_TIMEOUT, allow_redirects=True)
        # Some sites block HEAD, fall back to GET
        if resp.status_code >= 400:
            resp = requests.get(url, timeout=LINK_CHECK_TIMEOUT, allow_redirects=True, stream=True)
        if resp.status_code >= 400:
            errors.append(ValidationError(field_name, f"URL returned HTTP {resp.status_code}: {url}"))
    except requests.exceptions.Timeout:
        errors.append(ValidationError(field_name, f"URL timed out after {LINK_CHECK_TIMEOUT}s: {url}"))
    except requests.exceptions.ConnectionError:
        errors.append(ValidationError(field_name, f"Could not connect to URL: {url}"))
    except Exception as e:
        errors.append(ValidationError(field_name, f"Error checking URL: {e}"))
    return errors


def validate_submission(filepath):
    """Validate a single submission.yaml file. Returns a list of ValidationError."""
    errors = []

    # ── Parse YAML ──────────────────────────────────────────
    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [ValidationError("yaml", f"Failed to parse YAML: {e}")]
    except FileNotFoundError:
        return [ValidationError("file", f"File not found: {filepath}")]

    if not isinstance(data, dict):
        return [ValidationError("yaml", "YAML root must be a mapping")]

    # ── Directory name check ────────────────────────────────
    submission_dir = os.path.basename(os.path.dirname(filepath))
    if submission_dir.startswith("."):
        pass  # skip check for .example
    elif not DIR_NAME_PATTERN.match(submission_dir):
        errors.append(ValidationError(
            "directory",
            f"Directory name '{submission_dir}' must be lowercase alphanumeric with hyphens (e.g. 'my-method-name')"
        ))

    # ── Required top-level fields ───────────────────────────
    for field in REQUIRED_TOP_LEVEL:
        if field not in data or data[field] is None:
            errors.append(ValidationError(field, f"Required field '{field}' is missing"))

    # If critical fields are missing, no point continuing
    if any(e.field in REQUIRED_TOP_LEVEL for e in errors):
        return errors

    # ── name ────────────────────────────────────────────────
    if not isinstance(data["name"], str) or len(data["name"].strip()) == 0:
        errors.append(ValidationError("name", "Must be a non-empty string"))

    # ── description ─────────────────────────────────────────
    if not isinstance(data["description"], str) or len(data["description"].strip()) == 0:
        errors.append(ValidationError("description", "Must be a non-empty string"))

    # ── authors ─────────────────────────────────────────────
    authors = data["authors"]
    if not isinstance(authors, list) or len(authors) == 0:
        errors.append(ValidationError("authors", "Must be a list with at least one author"))
    else:
        for i, author in enumerate(authors):
            if not isinstance(author, dict):
                errors.append(ValidationError(f"authors[{i}]", "Each author must be a mapping"))
                continue
            if "name" not in author or not author["name"]:
                errors.append(ValidationError(f"authors[{i}].name", "Author name is required"))

    # ── code_url ────────────────────────────────────────────
    code_url = data.get("code_url", "")
    if not isinstance(code_url, str) or not code_url.startswith("http"):
        errors.append(ValidationError("code_url", "Must be a valid URL starting with http(s)"))
    else:
        errors.extend(check_url_resolves(code_url, "code_url"))

    # ── Optional URL fields ─────────────────────────────────
    for field in OPTIONAL_URL_FIELDS:
        value = data.get(field, "")
        if value and isinstance(value, str) and value.strip():
            if not value.startswith("http"):
                errors.append(ValidationError(field, "Must be a valid URL starting with http(s)"))
            else:
                errors.extend(check_url_resolves(value, field))

    # ── versions ────────────────────────────────────────────
    versions = data["versions"]
    if not isinstance(versions, list) or len(versions) == 0:
        errors.append(ValidationError("versions", "Must be a list with at least one version"))
    else:
        for i, ver in enumerate(versions):
            prefix = f"versions[{i}]"
            if not isinstance(ver, dict):
                errors.append(ValidationError(prefix, "Each version must be a mapping"))
                continue

            # Required version fields
            for vfield in ["version", "date", "scores"]:
                if vfield not in ver or ver[vfield] is None:
                    errors.append(ValidationError(f"{prefix}.{vfield}", f"Required field '{vfield}' is missing"))

            # scores
            scores = ver.get("scores")
            if scores is not None:
                if not isinstance(scores, list) or len(scores) == 0:
                    errors.append(ValidationError(f"{prefix}.scores", "Must be a list with at least one score entry"))
                else:
                    for k, score_val in enumerate(scores):
                        bprefix = f"{prefix}.scores[{k}]"
                        if not isinstance(score_val, dict):
                            errors.append(ValidationError(bprefix, f"Each score entry must be a mapping, got: {type(score_val).__name__}"))
                            continue

                        # benchmark (required)
                        benchmark = score_val.get("benchmark")
                        if not benchmark:
                            errors.append(ValidationError(f"{bprefix}.benchmark", "Required field 'benchmark' is missing"))
                            benchmark = None
                        elif benchmark not in VALID_ARC_VERSIONS:
                            errors.append(ValidationError(
                                f"{bprefix}.benchmark",
                                f"Invalid benchmark '{benchmark}'. Must be one of: {', '.join(sorted(VALID_ARC_VERSIONS))}"
                            ))
                            benchmark = None

                        # score / scorecard_url — rules differ by benchmark
                        raw_score = score_val.get("score")
                        scorecard_url = score_val.get("scorecard_url")

                        if benchmark is None:
                            pass  # already reported an error above; skip further checks
                        elif benchmark == "arc-agi-3":
                            # arc-agi-3: scorecard_url required, score not allowed
                            if raw_score is not None:
                                errors.append(ValidationError(
                                    f"{bprefix}.score",
                                    "arc-agi-3 scores are pulled from the scorecard — do not include a 'score' field; use 'scorecard_url' instead"
                                ))
                            if not scorecard_url:
                                errors.append(ValidationError(f"{bprefix}.scorecard_url", "scorecard_url is required for arc-agi-3 entries"))
                            else:
                                if not isinstance(scorecard_url, str) or not scorecard_url.startswith("http"):
                                    errors.append(ValidationError(f"{bprefix}.scorecard_url", "Must be a valid URL starting with http(s)"))
                                else:
                                    errors.extend(check_url_resolves(scorecard_url, f"{bprefix}.scorecard_url"))
                        else:
                            # arc-agi-1 / arc-agi-2: score required, scorecard_url not allowed
                            if scorecard_url is not None:
                                errors.append(ValidationError(
                                    f"{bprefix}.scorecard_url",
                                    "scorecard_url is only available for arc-agi-3 entries; remove it for arc-agi-1/arc-agi-2"
                                ))
                            if raw_score is None:
                                errors.append(ValidationError(f"{bprefix}.score", "Required field 'score' is missing"))
                                numeric_score = None
                            elif not isinstance(raw_score, (int, float)):
                                errors.append(ValidationError(f"{bprefix}.score", f"Must be a number, got: {type(raw_score).__name__}"))
                                numeric_score = None
                            else:
                                numeric_score = raw_score
                            if raw_score is not None and isinstance(raw_score, (int, float)):
                                if raw_score < 0 or raw_score > 100:
                                    errors.append(ValidationError(f"{bprefix}.score", f"Must be between 0 and 100, got: {raw_score}"))

                        # set (required)
                        set_val = score_val.get("set")
                        if not set_val or not isinstance(set_val, str):
                            errors.append(ValidationError(f"{bprefix}.set", "Required field 'set' is missing or empty"))

                        # cost (optional, must be non-negative)
                        cost = score_val.get("cost")
                        if cost is not None:
                            if not isinstance(cost, (int, float)) or cost < 0:
                                errors.append(ValidationError(f"{bprefix}.cost", "Must be a non-negative number"))

            # date
            date_val = ver.get("date")
            if date_val is not None:
                if isinstance(date_val, datetime):
                    pass  # PyYAML auto-parses dates
                elif isinstance(date_val, str):
                    try:
                        datetime.strptime(date_val, "%Y-%m-%d")
                    except ValueError:
                        errors.append(ValidationError(f"{prefix}.date", f"Must be YYYY-MM-DD format, got: '{date_val}'"))
                else:
                    # Could be a date object from YAML parsing
                    pass

            # models
            models = ver.get("models")
            if models is not None:
                if not isinstance(models, list) or len(models) == 0:
                    errors.append(ValidationError(f"{prefix}.models", "Must be a list with at least one model"))
                else:
                    for j, model in enumerate(models):
                        mprefix = f"{prefix}.models[{j}]"
                        if not isinstance(model, dict):
                            errors.append(ValidationError(mprefix, "Each model must be a mapping"))
                            continue
                        if "name" not in model or not model["name"]:
                            errors.append(ValidationError(f"{mprefix}.name", "Model name is required"))

    # ── Duplicate name check across repo ────────────────────
    submissions_dir = os.path.join(os.path.dirname(filepath), "..")
    submission_name = data.get("name", "")
    current_dir = os.path.basename(os.path.dirname(filepath))

    if os.path.isdir(submissions_dir):
        for entry in os.listdir(submissions_dir):
            if entry == current_dir or entry.startswith("."):
                continue
            other_yaml = os.path.join(submissions_dir, entry, "submission.yaml")
            if os.path.isfile(other_yaml):
                try:
                    with open(other_yaml, "r") as f:
                        other_data = yaml.safe_load(f)
                    if isinstance(other_data, dict) and other_data.get("name") == submission_name:
                        errors.append(ValidationError(
                            "name",
                            f"Duplicate name '{submission_name}' — already used by submission '{entry}'"
                        ))
                except Exception:
                    pass  # Don't fail validation because of another file's issues

    return errors


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    files = [f.strip() for f in sys.argv[1:] if f.strip()]

    if not files:
        print("⚠ No submission files to validate.")
        print("  Make sure your submission.yaml is at submissions/<your-id>/submission.yaml")
        sys.exit(0)

    all_passed = True

    for filepath in files:
        print(f"\n{'─' * 60}")
        print(f"Validating: {filepath}")
        print(f"{'─' * 60}")

        errors = validate_submission(filepath)

        if errors:
            all_passed = False
            print(f"\n  ✗ FAILED — {len(errors)} error(s):\n")
            for error in errors:
                print(f"  {error}")
        else:
            print(f"\n  ✓ PASSED")

    print(f"\n{'═' * 60}")
    if all_passed:
        print("All submissions passed validation ✓")
        sys.exit(0)
    else:
        print("Some submissions failed validation ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
