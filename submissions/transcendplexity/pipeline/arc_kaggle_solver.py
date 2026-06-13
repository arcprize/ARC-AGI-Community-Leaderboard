#!/usr/bin/env python3
"""
ARC-AGI Automated Solver — Kaggle Competition Pipeline

Runtime program synthesis: takes unseen ARC tasks, generates Python solvers
using LLM, tests against training examples, iterates until correct.

Uses 514 catalog solvers as few-shot examples for the LLM.

Usage:
    # Solve all evaluation tasks (API mode)
    export ANTHROPIC_API_KEY="your-key"  # or OPENAI_API_KEY
    python arc_kaggle_solver.py --data arc_data/data/evaluation --out submission.json

    # Solve a single task
    python arc_kaggle_solver.py --task abc82100 --data arc_data/data/evaluation

    # Use Ollama (local, free)
    python arc_kaggle_solver.py --backend ollama --model qwen2.5-coder:14b

    # Dry run on N tasks
    python arc_kaggle_solver.py --data arc_data/data/evaluation --limit 10

Backends:
    anthropic   — Claude API (best quality, needs ANTHROPIC_API_KEY)
    openai      — GPT API (needs OPENAI_API_KEY)
    ollama      — Local Ollama server (free, needs ollama running)
"""

import json
import os
import sys
import time
import glob
import random
import signal
import importlib.util
import traceback
import argparse
import textwrap
from pathlib import Path
from typing import Optional
from multiprocessing import Process, Queue
from collections import defaultdict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CATALOG_DIR = os.path.join(os.path.dirname(__file__), "arc-puzzle-catalog", "solves")
MAX_ATTEMPTS = 6          # Max LLM iterations per task
EXEC_TIMEOUT = 10         # Seconds per solver execution
MAX_FEW_SHOT = 3          # Number of catalog examples in prompt
TEMPERATURES = [0.0, 0.3, 0.7, 1.0, 0.5, 0.9]  # Per attempt

ARC_COLORS = {
    0: "black", 1: "blue", 2: "red", 3: "green", 4: "yellow",
    5: "gray", 6: "magenta", 7: "orange", 8: "cyan", 9: "maroon"
}


# ---------------------------------------------------------------------------
# Grid utilities
# ---------------------------------------------------------------------------

def grid_to_str(grid: list[list[int]]) -> str:
    """Compact grid string for LLM prompts."""
    return "\n".join(" ".join(str(c) for c in row) for row in grid)


def grid_dims(grid: list[list[int]]) -> str:
    return f"{len(grid)}x{len(grid[0])}"


def grid_colors(grid: list[list[int]]) -> set:
    return {c for row in grid for c in row}


def grid_signature(task: dict) -> dict:
    """Extract structural features for few-shot retrieval."""
    train = task["train"]
    sigs = []
    for ex in train:
        inp, out = ex["input"], ex["output"]
        sigs.append({
            "in_h": len(inp), "in_w": len(inp[0]),
            "out_h": len(out), "out_w": len(out[0]),
            "in_colors": len(grid_colors(inp)),
            "out_colors": len(grid_colors(out)),
            "size_change": len(out) != len(inp) or len(out[0]) != len(inp[0]),
            "color_change": grid_colors(out) != grid_colors(inp),
        })
    return {
        "num_train": len(train),
        "num_test": len(task.get("test", [])),
        "examples": sigs,
        "any_size_change": any(s["size_change"] for s in sigs),
        "any_color_change": any(s["color_change"] for s in sigs),
        "max_grid": max(max(s["in_h"], s["in_w"], s["out_h"], s["out_w"]) for s in sigs),
    }


# ---------------------------------------------------------------------------
# Catalog: load few-shot examples from 514 solved tasks
# ---------------------------------------------------------------------------

_catalog_cache = {}

def load_catalog() -> dict:
    """Load solver catalog: {task_id: solver_code}."""
    global _catalog_cache
    if _catalog_cache:
        return _catalog_cache

    if not os.path.isdir(CATALOG_DIR):
        print(f"[WARN] Catalog not found at {CATALOG_DIR}")
        return {}

    for task_dir in sorted(os.listdir(CATALOG_DIR)):
        solver_path = os.path.join(CATALOG_DIR, task_dir, "solver.py")
        if os.path.isfile(solver_path):
            try:
                code = open(solver_path).read()
                _catalog_cache[task_dir] = code
            except Exception:
                pass

    print(f"[CATALOG] Loaded {len(_catalog_cache)} solvers")
    return _catalog_cache


def pick_few_shot(task: dict, n: int = MAX_FEW_SHOT) -> list[tuple[str, str]]:
    """Pick diverse catalog solvers as few-shot examples.

    Strategy: pick solvers of varying complexity (short, medium, long)
    that share structural features with the target task.
    """
    catalog = load_catalog()
    if not catalog:
        return []

    sig = grid_signature(task)
    items = list(catalog.items())

    # Score each solver by relevance
    scored = []
    for task_id, code in items:
        lines = len(code.strip().split("\n"))
        # Prefer solvers that are readable (20-150 lines)
        if lines < 10 or lines > 200:
            continue
        scored.append((task_id, code, lines))

    if not scored:
        return [(tid, code) for tid, code in random.sample(items, min(n, len(items)))]

    # Pick diverse: one short, one medium, one long
    scored.sort(key=lambda x: x[2])
    buckets = [
        scored[:len(scored)//3],           # short
        scored[len(scored)//3:2*len(scored)//3],  # medium
        scored[2*len(scored)//3:],         # long
    ]

    picks = []
    for bucket in buckets:
        if bucket and len(picks) < n:
            choice = random.choice(bucket)
            picks.append((choice[0], choice[1]))

    return picks[:n]


# ---------------------------------------------------------------------------
# LLM Backends
# ---------------------------------------------------------------------------

def call_anthropic(prompt: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    """Call Anthropic Claude API."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def call_openai(prompt: str, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    """Call OpenAI API."""
    import openai
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="o3-mini",
        max_completion_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def call_ollama(prompt: str, temperature: float = 0.0, max_tokens: int = 4096,
                model: str = "qwen2.5-coder:14b") -> str:
    """Call local Ollama server."""
    import requests
    resp = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }, timeout=180)
    return resp.json().get("response", "")


def get_llm_caller(backend: str, model: Optional[str] = None):
    """Return a callable (prompt, temperature) -> response_text."""
    if backend == "anthropic":
        return lambda p, t: call_anthropic(p, t)
    elif backend == "openai":
        return lambda p, t: call_openai(p, t)
    elif backend == "ollama":
        m = model or "qwen2.5-coder:14b"
        return lambda p, t: call_ollama(p, t, model=m)
    else:
        raise ValueError(f"Unknown backend: {backend}")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_solve_prompt(task: dict, few_shot: list[tuple[str, str]],
                       feedback: str = "", attempt: int = 0) -> str:
    """Build the program synthesis prompt."""

    parts = [textwrap.dedent("""\
        You are an expert ARC-AGI puzzle solver. Your job is to analyze the training
        examples, discover the transformation rule, and write a Python function that
        implements it.

        RULES:
        - Write a function: def solve(grid: list[list[int]]) -> list[list[int]]
        - Input grid is a 2D list of ints (0-9 representing colors)
        - Output grid is a 2D list of ints (may be different size)
        - Use ONLY Python standard library (no numpy, no external packages)
        - The function must work on ANY input following the same rule, not just the examples
        - Return ONLY the Python code inside ```python ... ``` markers

        COLOR KEY: 0=black 1=blue 2=red 3=green 4=yellow 5=gray 6=magenta 7=orange 8=cyan 9=maroon
    """)]

    # Few-shot examples from catalog
    if few_shot and attempt == 0:
        parts.append("Here are examples of correctly solved ARC puzzles:\n")
        for tid, code in few_shot[:2]:  # Keep prompt manageable
            # Truncate very long solvers
            lines = code.strip().split("\n")
            if len(lines) > 60:
                code = "\n".join(lines[:60]) + "\n# ... (truncated)"
            parts.append(f"--- Solver for task {tid} ---")
            parts.append(f"```python\n{code.strip()}\n```\n")

    # The target task
    parts.append("=" * 60)
    parts.append("NOW SOLVE THIS PUZZLE:\n")

    for i, ex in enumerate(task["train"]):
        inp, out = ex["input"], ex["output"]
        parts.append(f"Training Example {i+1}:")
        parts.append(f"Input ({grid_dims(inp)}):")
        parts.append(grid_to_str(inp))
        parts.append(f"Output ({grid_dims(out)}):")
        parts.append(grid_to_str(out))
        parts.append("")

    # Show test input dimensions
    if task.get("test"):
        test_inp = task["test"][0]["input"]
        parts.append(f"Test Input ({grid_dims(test_inp)}):")
        parts.append(grid_to_str(test_inp))
        parts.append("")

    # Add feedback from previous failed attempt
    if feedback:
        parts.append("YOUR PREVIOUS ATTEMPT FAILED. Here is what went wrong:")
        parts.append(feedback)
        parts.append("\nFix the issues and try again. Think more carefully about the pattern.")
        parts.append("Analyze each training example step by step before writing code.")

    parts.append("\nThink step by step:")
    parts.append("1. What changes between input and output?")
    parts.append("2. What stays the same?")
    parts.append("3. What is the rule?")
    parts.append("4. Write the solve() function.\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Code extraction and sandboxed execution
# ---------------------------------------------------------------------------

def extract_code(response: str) -> Optional[str]:
    """Extract Python function from LLM response."""
    # Try ```python ... ``` block
    if "```python" in response:
        code = response.split("```python")[1].split("```")[0]
    elif "```" in response:
        blocks = response.split("```")
        code = None
        for i in range(1, len(blocks), 2):
            if "def solve" in blocks[i] or "def transform" in blocks[i]:
                code = blocks[i]
                break
        if code is None and len(blocks) > 1:
            code = blocks[1]
        if code is None:
            return None
    elif "def solve" in response:
        lines = response.split("\n")
        start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("def solve"):
                start = i
                break
        if start is not None:
            code = "\n".join(lines[start:])
        else:
            return None
    else:
        return None

    code = code.strip()

    # Normalize function name to solve()
    if "def transform(" in code and "def solve(" not in code:
        code = code.replace("def transform(", "def solve(")

    # Remove any language tag on first line
    if code and code.split("\n")[0].strip() in ("python", "py"):
        code = "\n".join(code.split("\n")[1:])

    return code


def _run_solver_in_process(code: str, grid: list, result_queue: Queue):
    """Execute solver code in a subprocess (for timeout safety)."""
    try:
        namespace = {}
        exec(code, namespace)
        solve_fn = namespace.get("solve") or namespace.get("transform")
        if solve_fn is None:
            result_queue.put(("error", "No solve() or transform() function found"))
            return
        import copy
        result = solve_fn(copy.deepcopy(grid))
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {e}"))


def run_solver(code: str, grid: list[list[int]], timeout: int = EXEC_TIMEOUT) -> tuple:
    """Run solver code safely with timeout. Returns (success, result_or_error)."""
    q: Queue = Queue()
    p = Process(target=_run_solver_in_process, args=(code, grid, q))
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join(1)
        return False, "TIMEOUT: solver took too long"

    if q.empty():
        return False, "No result returned (crash?)"

    status, result = q.get()
    if status == "ok":
        # Validate output format
        if not isinstance(result, list) or not all(isinstance(row, list) for row in result):
            return False, f"Invalid output type: expected list[list[int]], got {type(result)}"
        return True, result
    else:
        return False, result


# ---------------------------------------------------------------------------
# Solver verification
# ---------------------------------------------------------------------------

def verify_on_training(code: str, task: dict) -> tuple[bool, str]:
    """Test solver against all training examples. Returns (all_pass, feedback)."""
    feedback_parts = []
    all_pass = True
    num_examples = len(task["train"])

    for i, ex in enumerate(task["train"]):
        success, result = run_solver(code, ex["input"])

        if not success:
            all_pass = False
            feedback_parts.append(
                f"Example {i+1}/{num_examples} ERROR: {result}"
            )
            continue

        expected = ex["output"]
        if result == expected:
            feedback_parts.append(f"Example {i+1}/{num_examples}: PASS")
        else:
            all_pass = False
            # Compute detailed diff
            exp_h, exp_w = len(expected), len(expected[0])
            got_h = len(result)
            got_w = len(result[0]) if result else 0

            if got_h != exp_h or got_w != exp_w:
                feedback_parts.append(
                    f"Example {i+1}/{num_examples} FAIL: Wrong size. "
                    f"Expected {exp_h}x{exp_w}, got {got_h}x{got_w}"
                )
            else:
                wrong_cells = []
                for r in range(exp_h):
                    for c in range(exp_w):
                        if result[r][c] != expected[r][c]:
                            wrong_cells.append(
                                f"  [{r},{c}]: expected {expected[r][c]} got {result[r][c]}"
                            )
                feedback_parts.append(
                    f"Example {i+1}/{num_examples} FAIL: {len(wrong_cells)} wrong cells "
                    f"(out of {exp_h*exp_w}):"
                )
                # Show first 10 wrong cells
                for line in wrong_cells[:10]:
                    feedback_parts.append(line)
                if len(wrong_cells) > 10:
                    feedback_parts.append(f"  ... and {len(wrong_cells)-10} more")

                # Show expected vs got grids (compact)
                feedback_parts.append(f"Expected output:\n{grid_to_str(expected)}")
                feedback_parts.append(f"Your output:\n{grid_to_str(result)}")

    return all_pass, "\n".join(feedback_parts)


# ---------------------------------------------------------------------------
# Main solver loop
# ---------------------------------------------------------------------------

def solve_task(task_id: str, task: dict, llm_call, max_attempts: int = MAX_ATTEMPTS,
               verbose: bool = True) -> dict:
    """Solve a single ARC task using iterative program synthesis.

    Returns dict with:
        solved: bool
        predictions: list of predicted output grids for test inputs
        code: the working solver code (if solved)
        attempts: number of attempts used
    """
    few_shot = pick_few_shot(task)
    feedback = ""
    best_code = None
    best_score = -1

    for attempt in range(max_attempts):
        temp = TEMPERATURES[attempt % len(TEMPERATURES)]

        if verbose:
            status = "FIRST" if attempt == 0 else f"RETRY (t={temp:.1f})"
            print(f"  [{task_id}] Attempt {attempt+1}/{max_attempts} ({status})")

        # Build prompt
        prompt = build_solve_prompt(task, few_shot, feedback=feedback, attempt=attempt)

        # Call LLM
        try:
            response = llm_call(prompt, temp)
        except Exception as e:
            if verbose:
                print(f"  [{task_id}] LLM error: {e}")
            continue

        # Extract code
        code = extract_code(response)
        if code is None:
            feedback = "Could not extract a valid Python function from your response. Make sure to wrap your code in ```python ... ``` markers and define a function called solve()."
            if verbose:
                print(f"  [{task_id}] No code extracted")
            continue

        # Verify on training examples
        all_pass, verify_feedback = verify_on_training(code, task)

        # Track best partial solution
        pass_count = verify_feedback.count("PASS")
        if pass_count > best_score:
            best_score = pass_count
            best_code = code

        if all_pass:
            if verbose:
                print(f"  [{task_id}] SOLVED on attempt {attempt+1}!")

            # Apply to test inputs
            predictions = []
            for test_ex in task.get("test", []):
                success, result = run_solver(code, test_ex["input"])
                if success:
                    predictions.append(result)
                else:
                    predictions.append(None)

            return {
                "solved": True,
                "predictions": predictions,
                "code": code,
                "attempts": attempt + 1,
            }
        else:
            feedback = verify_feedback
            if verbose:
                passed = verify_feedback.count("PASS")
                total = len(task["train"])
                print(f"  [{task_id}] {passed}/{total} training examples passed")

    # Failed — use best partial code for predictions
    predictions = []
    if best_code:
        for test_ex in task.get("test", []):
            success, result = run_solver(best_code, test_ex["input"])
            if success:
                predictions.append(result)
            else:
                predictions.append(None)

    return {
        "solved": False,
        "predictions": predictions,
        "code": best_code,
        "attempts": max_attempts,
    }


# ---------------------------------------------------------------------------
# Check catalog for pre-solved tasks
# ---------------------------------------------------------------------------

def check_catalog(task_id: str, task: dict) -> Optional[dict]:
    """Check if task is already solved in the catalog."""
    catalog = load_catalog()
    code = catalog.get(task_id)
    if code is None:
        return None

    # Verify it still works
    all_pass, _ = verify_on_training(code, task)
    if not all_pass:
        return None

    # Apply to test
    predictions = []
    for test_ex in task.get("test", []):
        success, result = run_solver(code, test_ex["input"])
        if success:
            predictions.append(result)
        else:
            return None  # Catalog solver broken

    return {
        "solved": True,
        "predictions": predictions,
        "code": code,
        "attempts": 0,
        "source": "catalog",
    }


# ---------------------------------------------------------------------------
# Batch solver
# ---------------------------------------------------------------------------

def solve_batch(data_dir: str, llm_call, limit: Optional[int] = None,
                output_path: str = "submission.json",
                verbose: bool = True) -> dict:
    """Solve all tasks in a directory."""
    task_files = sorted(glob.glob(os.path.join(data_dir, "*.json")))
    if limit:
        task_files = task_files[:limit]

    print(f"\n{'='*60}")
    print(f" ARC-AGI Automated Solver")
    print(f" Tasks: {len(task_files)} | Max attempts: {MAX_ATTEMPTS}")
    print(f" Catalog: {len(load_catalog())} pre-solved")
    print(f"{'='*60}\n")

    results = {}
    submission = {}
    solved = 0
    catalog_hits = 0
    total = len(task_files)
    t0 = time.time()

    for idx, task_file in enumerate(task_files):
        task_id = Path(task_file).stem
        task = json.load(open(task_file))

        print(f"[{idx+1}/{total}] {task_id}", end="")

        # Check catalog first
        catalog_result = check_catalog(task_id, task)
        if catalog_result:
            results[task_id] = catalog_result
            catalog_hits += 1
            solved += 1
            print(f" -> CATALOG HIT")
        else:
            print()
            result = solve_task(task_id, task, llm_call, verbose=verbose)
            results[task_id] = result
            if result["solved"]:
                solved += 1

        # Build submission entry
        r = results[task_id]
        task_preds = {}
        for i, pred in enumerate(r.get("predictions", [])):
            if pred is not None:
                task_preds[str(i)] = pred
            else:
                # Fallback: copy test input
                task_preds[str(i)] = task["test"][i]["input"]
        submission[task_id] = task_preds

        elapsed = time.time() - t0
        rate = (idx + 1) / elapsed if elapsed > 0 else 0
        eta = (total - idx - 1) / rate if rate > 0 else 0
        print(f"  Score: {solved}/{idx+1} ({solved/(idx+1)*100:.1f}%) | "
              f"ETA: {eta/60:.0f}min\n")

    # Save submission
    with open(output_path, "w") as f:
        json.dump(submission, f, indent=2)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f" RESULTS")
    print(f"{'='*60}")
    print(f" Solved: {solved}/{total} ({solved/max(total,1)*100:.1f}%)")
    print(f" Catalog hits: {catalog_hits}")
    print(f" LLM solved: {solved - catalog_hits}")
    print(f" Time: {elapsed:.0f}s ({elapsed/max(total,1):.1f}s/task)")
    print(f" Submission: {output_path}")
    print(f"{'='*60}\n")

    return {
        "solved": solved,
        "total": total,
        "catalog_hits": catalog_hits,
        "llm_solved": solved - catalog_hits,
        "time": elapsed,
        "results": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ARC-AGI Automated Solver")
    parser.add_argument("--data", default="arc_data/data/evaluation",
                        help="Directory containing ARC task JSON files")
    parser.add_argument("--task", help="Solve a single task by ID")
    parser.add_argument("--out", default="submission.json",
                        help="Output submission file")
    parser.add_argument("--backend", default="anthropic",
                        choices=["anthropic", "openai", "ollama"],
                        help="LLM backend")
    parser.add_argument("--model", help="Model name (for ollama)")
    parser.add_argument("--limit", type=int, help="Max tasks to solve")
    parser.add_argument("--attempts", type=int, default=6,
                        help="Max LLM attempts per task")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    max_attempts = args.attempts

    # Get LLM caller
    llm_call = get_llm_caller(args.backend, args.model)

    if args.task:
        # Single task mode
        task_path = os.path.join(args.data, f"{args.task}.json")
        if not os.path.exists(task_path):
            # Try finding it
            candidates = glob.glob(os.path.join(args.data, f"*{args.task}*.json"))
            if candidates:
                task_path = candidates[0]
            else:
                print(f"Task not found: {args.task}")
                sys.exit(1)

        task = json.load(open(task_path))
        task_id = Path(task_path).stem

        # Check catalog first
        catalog_result = check_catalog(task_id, task)
        if catalog_result:
            print(f"[{task_id}] CATALOG HIT - already solved!")
            print(f"Predictions: {len(catalog_result['predictions'])} test outputs")
            return

        result = solve_task(task_id, task, llm_call, verbose=True)
        if result["solved"]:
            print(f"\nSOLVED in {result['attempts']} attempts!")
            print(f"Code:\n{result['code']}")
        else:
            print(f"\nFAILED after {result['attempts']} attempts")
            if result["code"]:
                print(f"Best partial code:\n{result['code']}")
    else:
        # Batch mode
        solve_batch(
            args.data, llm_call,
            limit=args.limit,
            output_path=args.out,
            verbose=not args.quiet,
        )


if __name__ == "__main__":
    main()
