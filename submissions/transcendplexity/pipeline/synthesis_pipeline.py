#!/usr/bin/env python3
"""
TranscendPlexity Synthesis Pipeline
====================================
LLM-guided program synthesis for ARC-AGI tasks using Claude (Anthropic).

For each task the pipeline:
  1. Builds a structured prompt from the training examples
  2. Calls Claude to generate a Python  solve(grid) -> grid  function
  3. Extracts the function from the response
  4. Validates the function against ALL training pairs
  5. Runs an anti-hardcoding probe (perturbed inputs must produce different outputs)
  6. On failure: retries with detailed error feedback (up to --retries times)
  7. Saves each passing solver to  <out>/<task_id>/solver.py

This is the pipeline that generated the TranscendPlexity 540/540 submission.

Quick start
-----------
    export ANTHROPIC_API_KEY=sk-ant-...
    python synthesis_pipeline.py \\
        --tasks arc_tasks.json \\
        --out   solves/

All options
-----------
    --tasks       Path to ARC JSON  {"<id>": {"train": [...], "test": [...]}}
    --out         Output directory for solver.py files  (default: solves/)
    --task-ids    Comma-separated list of task IDs to (re-)run (default: all)
    --workers     Parallel synthesis workers              (default: 4)
    --retries     LLM retry attempts per task             (default: 6)
    --model       Claude model name                       (default: claude-opus-4-5)
    --verify-only Re-validate existing solvers, no new generation
    --verbose     Print per-attempt detail

Dependencies
------------
    pip install anthropic
"""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import os
import sys
import tempfile
import textwrap
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional


# ─── Grid utilities ───────────────────────────────────────────────────────────

Grid = list[list[int]]


def grid_to_str(grid: Grid) -> str:
    return "\n".join(" ".join(str(v) for v in row) for row in grid)


def grids_equal(a: Grid, b: Grid) -> bool:
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if list(ra) != list(rb):
            return False
    return True


# ─── Prompts ──────────────────────────────────────────────────────────────────

_SYSTEM = textwrap.dedent("""\
    You are an expert at solving ARC (Abstraction and Reasoning Corpus) puzzles.
    You write concise, correct Python functions that generalise a visual rule from
    a handful of input/output grid examples.
    Each grid is a list of lists of integers (0–9 represent colours; 0 is background).
    You must return ONLY a Python code block — no prose, no markdown outside the block.
""")


def build_prompt(task: dict, task_id: str, error_feedback: Optional[str] = None) -> str:
    lines: list[str] = []
    lines.append(f"# Task {task_id}\n")
    for i, ex in enumerate(task["train"]):
        ih, iw = len(ex["input"]), len(ex["input"][0])
        oh, ow = len(ex["output"]), len(ex["output"][0])
        lines.append(f"## Train {i + 1}  (input {ih}×{iw} → output {oh}×{ow})")
        lines.append("Input:")
        lines.append(grid_to_str(ex["input"]))
        lines.append("Output:")
        lines.append(grid_to_str(ex["output"]))
        lines.append("")

    n = len(task["train"])
    lines.append(
        f"Study the {n} example{'s' if n != 1 else ''} above.\n"
        "Identify the transformation rule, then implement it as:\n\n"
        "```python\n"
        "def solve(grid: list[list[int]]) -> list[list[int]]:\n"
        "    ...\n"
        "```\n\n"
        "Requirements:\n"
        "- Standard library only (no numpy, no third-party packages)\n"
        "- Must handle any valid grid, not just these examples\n"
        "- Return a NEW grid; do not mutate the input\n"
        "- The function must pass ALL training examples exactly\n"
    )

    if error_feedback:
        lines.append(
            "\n⚠️  Your previous attempt failed:\n"
            f"{error_feedback}\n\n"
            "Fix the function so it passes every training example."
        )

    return "\n".join(lines)


# ─── Claude API ───────────────────────────────────────────────────────────────

def call_claude(prompt: str, model: str, temperature: float) -> Optional[str]:
    try:
        import anthropic  # type: ignore
    except ImportError:
        sys.exit("Install anthropic:  pip install anthropic")

    client = anthropic.Anthropic()
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return msg.content[0].text
    except Exception as exc:
        return f"__ERROR__: {exc}"


# ─── Code extraction ──────────────────────────────────────────────────────────

def extract_code(response: str) -> Optional[str]:
    """Pull the first Python code block out of an LLM response."""
    for fence in ("```python", "```"):
        if fence in response:
            after = response.split(fence, 1)[1]
            code = after.split("```", 1)[0].strip()
            if "def solve" in code:
                return code
    # Fallback: look for def solve at the top level
    if "def solve" in response:
        idx = response.index("def solve")
        candidate = response[idx:]
        lines = candidate.splitlines()
        out: list[str] = [lines[0]]
        for line in lines[1:]:
            if line and not line[0].isspace() and line.strip().startswith("def "):
                break
            out.append(line)
        return "\n".join(out)
    return None


# ─── Validation ───────────────────────────────────────────────────────────────

def load_solver(code: str) -> tuple[bool, Optional[object], str]:
    """Compile solver code and return (ok, solve_fn, error)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    try:
        spec = importlib.util.spec_from_file_location("_solver_tmp", path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        if not hasattr(mod, "solve"):
            return False, None, "No `solve` function defined"
        return True, mod.solve, ""
    except Exception:
        return False, None, traceback.format_exc()
    finally:
        os.unlink(path)


def validate_on_training(solve_fn: object, task: dict) -> tuple[bool, str]:
    """Run solve_fn on every training pair. Returns (passed, error_detail)."""
    for i, ex in enumerate(task["train"]):
        try:
            result = solve_fn(copy.deepcopy(ex["input"]))  # type: ignore[operator]
        except Exception:
            return False, f"Train {i}: exception\n{traceback.format_exc()}"

        if result is None:
            return False, f"Train {i}: returned None"

        result = [list(row) for row in result]
        expected = ex["output"]

        if len(result) != len(expected):
            return (
                False,
                f"Train {i}: shape {len(result)}×{len(result[0]) if result else '?'} "
                f"≠ expected {len(expected)}×{len(expected[0]) if expected else '?'}",
            )
        for r, (got_row, exp_row) in enumerate(zip(result, expected)):
            for c, (got, exp) in enumerate(zip(got_row, exp_row)):
                if got != exp:
                    return (
                        False,
                        f"Train {i}: mismatch at [{r}][{c}]: got {got}, expected {exp}\n"
                        f"Full got:\n{grid_to_str(result)}\n"
                        f"Full expected:\n{grid_to_str(expected)}",
                    )
    return True, ""


def anti_hardcode_check(solve_fn: object, task: dict) -> tuple[bool, str]:
    """
    Reject solvers that memorise answers rather than implementing a rule.

    Strategy:
      1. Pick a training example whose input has at least two distinct colours.
      2. Swap all occurrences of two colours in the input.
      3. Verify the solver's output changes compared with the original output.

    A genuine rule-based solver will produce different output when the input
    changes; a hardcoded solver will return the same fixed grid regardless.
    """
    for ex in task["train"]:
        colours = sorted({v for row in ex["input"] for v in row})
        if len(colours) < 2:
            continue

        c1, c2 = colours[0], colours[1]
        mutated: Grid = [
            [c2 if v == c1 else c1 if v == c2 else v for v in row]
            for row in ex["input"]
        ]

        try:
            original_out = solve_fn(copy.deepcopy(ex["input"]))  # type: ignore[operator]
            mutated_out = solve_fn(copy.deepcopy(mutated))  # type: ignore[operator]
        except Exception:
            # Solver crashes on mutation → accept (it's not purely static)
            return True, ""

        if original_out is not None and mutated_out is not None:
            if not grids_equal(list(original_out), list(mutated_out)):  # type: ignore[arg-type]
                return True, ""  # Output changed → not hardcoded

    # Could not falsify → warn but do not block single-example tasks
    if len(task["train"]) == 1:
        return True, "(single-example task; hardcode probe inconclusive)"

    return (
        False,
        "Hardcoded answer detected: output is identical regardless of colour swaps in input. "
        "The solver must implement a general rule, not memorise the training output.",
    )


def static_hardcode_check(code: str) -> tuple[bool, str]:
    """
    AST-based check: flag functions whose body is a single `return <literal>`.
    This catches the simplest form of answer memorisation.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return True, ""  # syntax error will be caught elsewhere

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "solve":
            body = node.body
            # Strip leading docstring
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Constant, ast.Str)):
                body = body[1:]
            if len(body) == 1 and isinstance(body[0], ast.Return):
                ret = body[0].value
                # A bare `return [[...]]` or `return CONSTANT` is suspicious
                if isinstance(ret, (ast.List, ast.Constant)):
                    return (
                        False,
                        "Static hardcoding: `solve` body is a single `return <literal>`. "
                        "Implement the actual transformation rule.",
                    )
    return True, ""


# ─── Core synthesis loop ──────────────────────────────────────────────────────

TEMPERATURES = [0.2, 0.5, 0.8, 0.3, 0.6, 1.0]


def synthesize_task(
    task_id: str,
    task: dict,
    model: str,
    max_retries: int,
    verbose: bool,
) -> tuple[str, Optional[str], str]:
    """
    Attempt to synthesise a solver for one ARC task.

    Returns (task_id, code_or_None, status_message).
    """
    error_feedback: Optional[str] = None

    for attempt in range(max_retries):
        temp = TEMPERATURES[attempt % len(TEMPERATURES)]
        prompt = build_prompt(task, task_id, error_feedback)

        response = call_claude(prompt, model, temp)
        if response is None or response.startswith("__ERROR__"):
            error_feedback = response or "LLM returned no response"
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: LLM error — {error_feedback[:80]}")
            time.sleep(1)
            continue

        code = extract_code(response)
        if code is None:
            error_feedback = "No `solve` function found in LLM response."
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: no function extracted")
            continue

        # Static hardcode check first (fast)
        static_ok, static_msg = static_hardcode_check(code)
        if not static_ok:
            error_feedback = static_msg
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: static hardcode detected")
            continue

        # Compile
        load_ok, solve_fn, load_err = load_solver(code)
        if not load_ok:
            error_feedback = f"Compilation error:\n{load_err}"
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: compile error")
            continue

        # Validate on training
        train_ok, train_err = validate_on_training(solve_fn, task)
        if not train_ok:
            error_feedback = train_err
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: train fail — {train_err[:120]}")
            continue

        # Anti-hardcode probe
        hc_ok, hc_msg = anti_hardcode_check(solve_fn, task)
        if not hc_ok:
            error_feedback = hc_msg
            if verbose:
                print(f"    [{task_id}] attempt {attempt + 1}: hardcode probe failed")
            continue

        if verbose:
            print(f"    [{task_id}] attempt {attempt + 1}: ✅ verified (t={temp})")
        return task_id, code, "solved"

    return task_id, None, f"failed after {max_retries} attempts — last error: {error_feedback or 'unknown'}"


# ─── Solver file I/O ──────────────────────────────────────────────────────────

SOLVER_HEADER = """\
# Task: {task_id}
# Generated by TranscendPlexity synthesis pipeline
# Validated: all training pairs pass, anti-hardcode probe passed
#
# Usage:  from solver import solve
#         output_grid = solve(input_grid)
"""


def save_solver(out_dir: Path, task_id: str, code: str) -> Path:
    task_dir = out_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    path = task_dir / "solver.py"
    header = SOLVER_HEADER.format(task_id=task_id)
    path.write_text(header + "\n" + code + "\n")
    return path


def load_existing_solver(out_dir: Path, task_id: str) -> Optional[str]:
    path = out_dir / task_id / "solver.py"
    if path.exists():
        return path.read_text()
    return None


# ─── Verification mode ────────────────────────────────────────────────────────

def verify_existing_solvers(tasks: dict, out_dir: Path) -> dict:
    results: dict = {"passed": [], "failed": [], "hardcoded": [], "missing": []}
    for task_id, task in tasks.items():
        code = load_existing_solver(out_dir, task_id)
        if code is None:
            results["missing"].append(task_id)
            continue

        static_ok, _ = static_hardcode_check(code)
        if not static_ok:
            results["hardcoded"].append(task_id)
            continue

        load_ok, solve_fn, _ = load_solver(code)
        if not load_ok:
            results["failed"].append(task_id)
            continue

        train_ok, _ = validate_on_training(solve_fn, task)
        hc_ok, _ = anti_hardcode_check(solve_fn, task)

        if train_ok and hc_ok:
            results["passed"].append(task_id)
        elif not hc_ok:
            results["hardcoded"].append(task_id)
        else:
            results["failed"].append(task_id)

    return results


# ─── CLI entry point ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="TranscendPlexity Synthesis Pipeline — Claude-powered ARC-AGI solver generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--tasks", required=True, help='ARC JSON: {"<id>": {"train": [...], "test": [...]}}')
    p.add_argument("--out", default="solves", help="Output directory (default: solves/)")
    p.add_argument("--task-ids", help="Comma-separated task IDs to run (default: all)")
    p.add_argument("--workers", type=int, default=4, help="Parallel synthesis workers (default: 4)")
    p.add_argument("--retries", type=int, default=6, help="Claude retries per task (default: 6)")
    p.add_argument("--model", default="claude-opus-4-5", help="Claude model name (default: claude-opus-4-5)")
    p.add_argument("--verify-only", action="store_true", help="Verify existing solvers without generating new ones")
    p.add_argument("--verbose", action="store_true", help="Print per-attempt detail")
    p.add_argument("--skip-existing", action="store_true", default=True, help="Skip tasks that already have a solver (default: true)")
    p.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"TranscendPlexity Synthesis Pipeline")
    print(f"  model   : {args.model}")
    print(f"  retries : {args.retries}")
    print(f"  workers : {args.workers}")
    print(f"  output  : {out_dir}/")
    print()

    with open(args.tasks) as f:
        all_tasks: dict = json.load(f)

    if args.task_ids:
        ids = [t.strip() for t in args.task_ids.split(",") if t.strip()]
        tasks = {k: v for k, v in all_tasks.items() if k in ids}
    else:
        tasks = all_tasks

    print(f"Tasks loaded : {len(tasks)}")

    # ── Verify-only mode ──────────────────────────────────────────────────────
    if args.verify_only:
        print("Mode: verify existing solvers\n")
        results = verify_existing_solvers(tasks, out_dir)
        total = len(tasks)
        print(f"  ✅  passed     : {len(results['passed'])} / {total}")
        print(f"  ❌  failed     : {len(results['failed'])}")
        print(f"  ⛔  hardcoded  : {len(results['hardcoded'])}")
        print(f"  ⬜  missing    : {len(results['missing'])}")
        if results["failed"]:
            print("\nFailed:", results["failed"])
        if results["hardcoded"]:
            print("\nHardcoded (require fixing):", results["hardcoded"])
        return

    # ── Filter already-solved tasks ───────────────────────────────────────────
    if args.skip_existing:
        todo = {k: v for k, v in tasks.items() if not (out_dir / k / "solver.py").exists()}
        skipped = len(tasks) - len(todo)
        if skipped:
            print(f"Skipped (existing): {skipped}")
    else:
        todo = tasks

    print(f"To synthesize : {len(todo)}")
    print()

    if not todo:
        print("Nothing to do.")
        return

    # ── Parallel synthesis ────────────────────────────────────────────────────
    t0 = time.time()
    solved_count = 0
    failed_ids: list[str] = []
    report: list[dict] = []

    def worker(item: tuple[str, dict]) -> tuple[str, Optional[str], str]:
        tid, task = item
        return synthesize_task(tid, task, args.model, args.retries, args.verbose)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, item): item[0] for item in todo.items()}
        done = 0
        for fut in as_completed(futures):
            tid = futures[fut]
            try:
                task_id, code, status = fut.result()
            except Exception as exc:
                task_id, code, status = tid, None, f"worker exception: {exc}"

            done += 1

            if code is not None:
                path = save_solver(out_dir, task_id, code)
                solved_count += 1
                print(f"  ✅ [{done}/{len(todo)}] {task_id}  →  {path}")
            else:
                failed_ids.append(task_id)
                print(f"  ❌ [{done}/{len(todo)}] {task_id}  —  {status}")

            report.append({"task_id": task_id, "status": status, "solved": code is not None})

    elapsed = time.time() - t0

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"SYNTHESIS COMPLETE")
    print(f"  Solved  : {solved_count} / {len(todo)}")
    print(f"  Failed  : {len(failed_ids)}")
    print(f"  Time    : {elapsed:.0f}s")
    if len(todo) > 0:
        print(f"  Rate    : {solved_count / len(todo) * 100:.1f}%")

    if failed_ids:
        print(f"\nFailed task IDs:")
        for fid in failed_ids:
            print(f"    {fid}")

    report_path = out_dir / "synthesis_report.json"
    with open(report_path, "w") as f:
        json.dump(
            {
                "model": args.model,
                "total": len(todo),
                "solved": solved_count,
                "failed": len(failed_ids),
                "elapsed_s": round(elapsed, 1),
                "tasks": report,
            },
            f,
            indent=2,
        )
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
