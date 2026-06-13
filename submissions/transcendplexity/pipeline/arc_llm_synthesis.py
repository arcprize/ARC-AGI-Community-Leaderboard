#!/usr/bin/env python3
"""ARC-AGI LLM Program Synthesis Solver.

Uses a local Ollama model to generate Python transform functions per task.
Key strategy: generate many candidates, verify against ALL training examples,
only accept programs that get 100% on training.

Designed to run locally under 20GB (model ~4.5GB + system).
"""
import json
import os
import sys
import time
import copy
import re
import traceback
import requests
import numpy as np
from typing import Optional, List, Tuple

EVAL_DIR = 'ARC_AMD_TRANSFER/data/ARC-AGI/data/evaluation'
OUTPUT_FILE = 'llm_eval_results.json'
OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'qwen2.5-coder:14b'

# ─── Grid Formatting ──────────────────────────────────────────────────────────

def grid_to_ascii(grid: list) -> str:
    """Format grid as compact ASCII with colors as digits."""
    return '\n'.join(' '.join(str(c) for c in row) for row in grid)

def format_task_prompt(task: dict, attempt: int = 0) -> str:
    """Format ARC task as a prompt for the LLM."""
    examples = []
    for i, p in enumerate(task['train']):
        inp_str = grid_to_ascii(p['input'])
        out_str = grid_to_ascii(p['output'])
        ih, iw = len(p['input']), len(p['input'][0])
        oh, ow = len(p['output']), len(p['output'][0])
        examples.append(
            f"Example {i+1} (input {ih}x{iw} -> output {oh}x{ow}):\n"
            f"Input:\n{inp_str}\n\n"
            f"Output:\n{out_str}"
        )
    
    test_inp = task['test'][0]['input']
    th, tw = len(test_inp), len(test_inp[0])
    test_str = grid_to_ascii(test_inp)
    
    base_prompt = f"""Solve this ARC-AGI puzzle. Study the input/output examples carefully to find the transformation rule, then write a Python function.

{chr(10).join(examples)}

Test input ({th}x{tw}):
{test_str}

Write a Python function `transform(grid)` where grid is a list of lists of ints (0-9).
The function must:
- Return the transformed grid as a list of lists
- Work correctly for ALL examples above
- NOT modify the input grid (use copy/deepcopy)
- Handle any valid grid size

Think step by step about what pattern transforms each input to its output.
"""

    if attempt == 0:
        suffix = "Write ONLY the function, no explanation."
    elif attempt == 1:
        suffix = "First describe the pattern you see in 1-2 sentences, then write the function."
    elif attempt == 2:
        suffix = "Look at what changes between input and output. Focus on colors, positions, and shapes. Write the function."
    elif attempt == 3:
        suffix = "Consider: rotations, reflections, color substitutions, filling regions, copying patterns, symmetry. Write the function."
    else:
        suffix = f"Try a different approach than before. Be creative. Write the function."
    
    return base_prompt + "\n" + suffix + "\n\n```python\n"

def format_task_prompt_compact(task: dict) -> str:
    """More compact prompt format using JSON-like grids."""
    examples = []
    for i, p in enumerate(task['train']):
        examples.append(f"In{i+1}: {p['input']}\nOut{i+1}: {p['output']}")
    
    test_inp = task['test'][0]['input']
    
    return f"""ARC puzzle. Find the rule that transforms input grids to output grids.

{chr(10).join(examples)}

Write `def transform(grid):` that works for all examples. grid is list[list[int]] with values 0-9. Return new grid, don't modify input.

```python
def transform(grid):
    import copy
    g = copy.deepcopy(grid)
"""

# ─── Code Extraction & Execution ──────────────────────────────────────────────

def extract_function(response: str) -> Optional[str]:
    """Extract Python function from LLM response."""
    # Try to find code blocks
    patterns = [
        r'```python\s*(def transform.*?)```',
        r'```\s*(def transform.*?)```',
        r'(def transform\(.*?\):.*?)(?:\n\n|\Z)',
    ]
    
    for pat in patterns:
        match = re.search(pat, response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            if 'def transform' in code:
                return code
    
    # Fallback: find def transform and take everything after
    idx = response.find('def transform')
    if idx >= 0:
        code = response[idx:]
        # Find end of function (next def or end)
        lines = code.split('\n')
        func_lines = [lines[0]]
        for line in lines[1:]:
            if line.strip() and not line[0].isspace() and not line.strip().startswith('#'):
                break
            func_lines.append(line)
        return '\n'.join(func_lines)
    
    return None


def execute_transform(code: str, input_grid: list, timeout: float = 5.0) -> Optional[list]:
    """Execute a transform function on an input grid with timeout."""
    import io
    import contextlib
    
    namespace = {'__builtins__': __builtins__}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exec(code, namespace)
    except Exception:
        return None
    
    if 'transform' not in namespace:
        return None
    
    transform_fn = namespace['transform']
    
    try:
        grid_copy = copy.deepcopy(input_grid)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = transform_fn(grid_copy)
        
        if result is None:
            return None
        if not isinstance(result, list):
            return None
        if len(result) == 0:
            return None
        for row in result:
            if not isinstance(row, (list, tuple)):
                return None
            for val in row:
                if not isinstance(val, (int, float, np.integer)):
                    return None
        
        # Convert to plain int lists
        return [[int(v) for v in row] for row in result]
    except Exception:
        return None


def verify_on_training(code: str, task: dict) -> Tuple[int, int]:
    """Verify a transform function against all training examples.
    Returns (correct_count, total_count)."""
    correct = 0
    total = len(task['train'])
    
    for p in task['train']:
        result = execute_transform(code, p['input'])
        if result is not None and result == p['output']:
            correct += 1
    
    return correct, total


# ─── LLM Interface ────────────────────────────────────────────────────────────

def generate_code(prompt: str, temperature: float = 0.3, max_tokens: int = 1500) -> Optional[str]:
    """Call Ollama to generate code."""
    try:
        resp = requests.post(OLLAMA_URL, json={
            'model': MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
                'top_p': 0.95,
            }
        }, timeout=120)
        
        if resp.status_code != 200:
            return None
        
        return resp.json().get('response', '')
    except Exception as e:
        print(f"    Ollama error: {e}")
        return None


# ─── Main Solver ──────────────────────────────────────────────────────────────

def solve_task_llm(task: dict, task_id: str, max_attempts: int = 8, verbose: bool = True) -> Optional[list]:
    """Try to solve a single ARC task using LLM program synthesis.
    
    Strategy:
    1. Generate code with different prompts and temperatures
    2. Verify each against all training examples
    3. Return first solution that gets 100% on training
    """
    temps = [0.1, 0.3, 0.5, 0.7, 0.3, 0.5, 0.7, 0.9]
    
    for attempt in range(max_attempts):
        # Alternate between verbose and compact prompts
        if attempt < 5:
            prompt = format_task_prompt(task, attempt=attempt)
        else:
            prompt = format_task_prompt_compact(task)
        
        temp = temps[attempt % len(temps)]
        
        response = generate_code(prompt, temperature=temp)
        if response is None:
            continue
        
        code = extract_function(response)
        if code is None:
            if verbose:
                print(f"    Attempt {attempt+1}: no valid function extracted")
            continue
        
        correct, total = verify_on_training(code, task)
        
        if verbose:
            print(f"    Attempt {attempt+1} (t={temp}): train {correct}/{total}", end='')
        
        if correct == total:
            # Perfect on training! Apply to test
            test_result = execute_transform(code, task['test'][0]['input'])
            if test_result is not None:
                if verbose:
                    print(f" ✅ -> test prediction generated")
                return test_result
            else:
                if verbose:
                    print(f" (test execution failed)")
        else:
            if verbose:
                print()
    
    return None


def main():
    print(f"ARC-AGI LLM Program Synthesis Solver")
    print(f"Model: {MODEL}")
    print(f"=" * 60)
    
    # Load already solved
    solved = set(json.load(open('arc_mega_eval_results.json'))['combined_ids'])
    print(f"Already solved (mega): {len(solved)}")
    
    # Load all unsolved eval tasks
    tasks_to_solve = []
    for fn in sorted(os.listdir(EVAL_DIR)):
        if not fn.endswith('.json'):
            continue
        tid = fn.replace('.json', '')
        if tid in solved:
            continue
        task = json.load(open(os.path.join(EVAL_DIR, fn)))
        
        # Prioritize: smaller grids first (faster, more likely to solve)
        max_cells = 0
        for p in task['train']:
            cells = len(p['input']) * len(p['input'][0])
            max_cells = max(max_cells, cells)
        
        tasks_to_solve.append((max_cells, tid, task))
    
    tasks_to_solve.sort()  # Smallest first
    print(f"Unsolved tasks: {len(tasks_to_solve)}")
    
    # Load previous results
    if os.path.exists(OUTPUT_FILE):
        prev = json.load(open(OUTPUT_FILE))
        results = prev.get('per_task', {})
        llm_solved = set(prev.get('solved_ids', []))
    else:
        results = {}
        llm_solved = set()
    
    new_this_run = 0
    
    for i, (cells, tid, task) in enumerate(tasks_to_solve):
        if tid in results:
            continue
        
        print(f"\n[{i+1}/{len(tasks_to_solve)}] {tid} ({cells} cells)")
        t0 = time.time()
        
        pred = solve_task_llm(task, tid, max_attempts=8, verbose=True)
        elapsed = time.time() - t0
        
        if pred is not None:
            gt = task['test'][0]['output']
            match = pred == gt
            results[tid] = {
                'correct': match,
                'time': elapsed,
                'prediction': pred if match else None,
            }
            
            if match:
                llm_solved.add(tid)
                new_this_run += 1
                print(f"  ✅ CORRECT! ({elapsed:.0f}s) [total new: {new_this_run}]")
            else:
                # Check cell accuracy
                pred_arr = np.array(pred)
                gt_arr = np.array(gt)
                if pred_arr.shape == gt_arr.shape:
                    cell_acc = (pred_arr == gt_arr).mean()
                    print(f"  ❌ Wrong ({cell_acc:.0%} cells) ({elapsed:.0f}s)")
                else:
                    print(f"  ❌ Shape mismatch ({elapsed:.0f}s)")
        else:
            results[tid] = {'correct': False, 'time': elapsed, 'no_solution': True}
            print(f"  ⚠ No valid solution found ({elapsed:.0f}s)")
        
        # Save every 5 tasks
        if (i + 1) % 5 == 0 or new_this_run > 0:
            combined = sorted(solved | llm_solved)
            out = {
                'llm_solved': len(llm_solved),
                'new_this_run': new_this_run,
                'combined': len(combined),
                'pct': len(combined) / 400 * 100,
                'solved_ids': sorted(llm_solved),
                'combined_ids': combined,
                'model': MODEL,
                'per_task': results,
            }
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(out, f, indent=2)
    
    # Final save
    combined = sorted(solved | llm_solved)
    out = {
        'llm_solved': len(llm_solved),
        'new_this_run': new_this_run,
        'combined': len(combined),
        'pct': len(combined) / 400 * 100,
        'solved_ids': sorted(llm_solved),
        'combined_ids': combined,
        'model': MODEL,
        'per_task': results,
    }
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(out, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"LLM solved: {len(llm_solved)} ({new_this_run} new this run)")
    print(f"Combined: {len(combined)}/400 ({len(combined)/4:.1f}%)")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
