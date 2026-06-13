#!/usr/bin/env python3
"""
Generate transform() solver functions for each RE-ARC task using Claude API.
Validates each solver against training data before saving.
Retries with error feedback up to MAX_RETRIES times per task.
"""
import json, os, sys, importlib.util, tempfile, traceback, time
import anthropic

DATASET_PATH = '/Users/evanpieser/Desktop/RE-ARC_SUBMISSION_READY/re-arc_test_challenges-2026-04-02T06-26-37.json'
SOLVER_DIR   = '/Users/evanpieser/re_arc_solvers_current'
MAX_RETRIES  = 3
MODEL        = 'claude-opus-4-5'

client = anthropic.Anthropic()

def grid_to_str(grid):
    return '\n'.join(' '.join(str(v) for v in row) for row in grid)

def format_task(task):
    lines = []
    for i, ex in enumerate(task['train']):
        lines.append(f'--- Train Example {i+1} ---')
        lines.append(f'Input ({len(ex["input"])} rows x {len(ex["input"][0])} cols):')
        lines.append(grid_to_str(ex['input']))
        lines.append(f'Output ({len(ex["output"])} rows x {len(ex["output"][0])} cols):')
        lines.append(grid_to_str(ex['output']))
    return '\n'.join(lines)

def build_prompt(task_id, task, error_feedback=None):
    task_str = format_task(task)
    n_train = len(task['train'])
    
    base = f"""You are solving an ARC (Abstraction and Reasoning Corpus) puzzle.

TASK ID: {task_id}

You will be given {n_train} training example(s). Each shows an input grid and an output grid.
Your job is to figure out the transformation rule and write a Python function that implements it.

GRIDS use integers 0-9 representing colors. 0 is typically background.

{task_str}

Write a Python function with this EXACT signature:
    def transform(grid: list[list[int]]) -> list[list[int]]:

Requirements:
- Use ONLY Python standard library (collections, itertools, etc.) -- NO numpy, NO imports not in stdlib
- The function must correctly reproduce ALL {n_train} training outputs from their inputs
- Handle edge cases (empty grids, single cells, etc.)
- Return a NEW grid (do not modify the input in-place)

Think carefully about:
1. What changes between input and output? (size change? color change? object movement?)
2. What stays the same?
3. What is the general rule that works for ALL examples?

Respond with ONLY the Python code block containing the transform function and any helper functions it needs.
Do not include any explanation outside the code block.
The code must start with `def transform(` or with helper function definitions followed by `def transform(`.
"""
    if error_feedback:
        base += f"""
PREVIOUS ATTEMPT FAILED with this error:
{error_feedback}

Fix the function to pass all training examples correctly.
"""
    return base

def extract_code(text):
    """Extract Python code from Claude's response."""
    # Try to find code block
    if '```python' in text:
        start = text.index('```python') + 9
        end = text.index('```', start)
        return text[start:end].strip()
    elif '```' in text:
        start = text.index('```') + 3
        end = text.index('```', start)
        return text[start:end].strip()
    else:
        # Assume the whole response is code
        return text.strip()

def validate_solver(code, task):
    """Validate solver code against all training examples. Returns (ok, error_msg)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        tmppath = f.name
    
    try:
        spec = importlib.util.spec_from_file_location('solver_tmp', tmppath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        transform = mod.transform
        
        for i, ex in enumerate(task['train']):
            result = transform(ex['input'])
            if result != ex['output']:
                # Show first differing cell
                exp = ex['output']
                r_rows = len(result)
                e_rows = len(exp)
                r_cols = len(result[0]) if result else 0
                e_cols = len(exp[0]) if exp else 0
                if r_rows != e_rows or r_cols != e_cols:
                    return False, f"Train {i}: output shape {r_rows}x{r_cols} != expected {e_rows}x{e_cols}"
                # Find first mismatch
                for ri in range(e_rows):
                    for ci in range(e_cols):
                        if result[ri][ci] != exp[ri][ci]:
                            return False, (
                                f"Train {i}: mismatch at [{ri}][{ci}]: got {result[ri][ci]}, "
                                f"expected {exp[ri][ci]}\n"
                                f"Got output:\n{grid_to_str(result)}\n"
                                f"Expected output:\n{grid_to_str(exp)}"
                            )
        return True, None
    except Exception as e:
        return False, traceback.format_exc()
    finally:
        os.unlink(tmppath)

def solve_task(task_id, task):
    """Generate and validate a solver for a task. Returns (code, attempts_used) or (None, MAX_RETRIES)."""
    error_feedback = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        prompt = build_prompt(task_id, task, error_feedback)
        
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                messages=[{'role': 'user', 'content': prompt}]
            )
            code = extract_code(resp.content[0].text)
        except Exception as e:
            error_feedback = f"API error: {e}"
            time.sleep(2)
            continue
        
        ok, err = validate_solver(code, task)
        if ok:
            return code, attempt
        else:
            error_feedback = err
    
    return None, MAX_RETRIES

def main():
    os.makedirs(SOLVER_DIR, exist_ok=True)
    
    with open(DATASET_PATH) as f:
        challenges = json.load(f)
    
    task_ids = sorted(challenges.keys())
    total = len(task_ids)
    
    # Check which are already solved
    existing = set(f[:-3] for f in os.listdir(SOLVER_DIR) if f.endswith('.py'))
    todo = [t for t in task_ids if t not in existing]
    
    print(f"Total tasks: {total}")
    print(f"Already solved: {len(existing)}")
    print(f"Remaining: {len(todo)}")
    print()
    
    solved = len(existing)
    failed = []
    
    for i, task_id in enumerate(todo):
        task = challenges[task_id]
        n_train = len(task['train'])
        print(f"[{i+1}/{len(todo)}] {task_id} ({n_train} train examples)... ", end='', flush=True)
        
        code, attempts = solve_task(task_id, task)
        
        if code is not None:
            solver_path = os.path.join(SOLVER_DIR, f'{task_id}.py')
            with open(solver_path, 'w') as f:
                f.write(code)
            solved += 1
            print(f"✅ (attempt {attempts})")
        else:
            failed.append(task_id)
            print(f"❌ (failed after {MAX_RETRIES} attempts)")
        
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    print(f"\n{'='*50}")
    print(f"DONE")
    print(f"Solved: {solved}/{total} ({solved/total*100:.1f}%)")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"Failed tasks: {failed}")
    print(f"Solvers saved to: {SOLVER_DIR}")

if __name__ == '__main__':
    main()
