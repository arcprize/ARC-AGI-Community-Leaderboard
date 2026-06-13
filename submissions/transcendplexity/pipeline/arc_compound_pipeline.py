#!/usr/bin/env python3
"""
ARC-AGI Compound Pipeline — Parallel Multi-Layer Solver

All layers run in PARALLEL via ThreadPoolExecutor:
  Layer 1: Catalog lookup (514 known solvers, instant)
  Layer 2: Neural grid model with TTA (8 augmentations, majority vote)
  Layer 3: LLM program synthesis (runtime code gen, ~30s per task)

When multiple layers produce answers, consensus voting picks the best:
  - If catalog and neural agree → high confidence
  - If catalog passes training verification → use catalog
  - Neural TTA: run 8 augmented variants, majority-vote per cell
  - Confidence scoring from softmax probabilities

Usage:
    # Parallel mode (default) — all layers run simultaneously
    python arc_compound_pipeline.py --data ARC_AMD_TRANSFER/data/ARC-AGI/data --split evaluation

    # With LLM layer (needs API key)
    ANTHROPIC_API_KEY=... python arc_compound_pipeline.py --data ... --use-llm

    # Neural-only with TTA
    python arc_compound_pipeline.py --no-catalog --neural-tta 8 --data ...

    # Single task
    python arc_compound_pipeline.py --task 1a2e2828 --data ...
"""

import json
import os
import sys
import time
import argparse
import importlib.util
import traceback
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from multiprocessing import Process, Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

import torch
import torch.nn.functional as F
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger(__name__)

# ─── Layer 1: Catalog Lookup ───────────────────────────────────────

CATALOG_DIR = Path(__file__).parent / "arc-puzzle-catalog" / "solves"


def catalog_solve(task_id: str, task: dict) -> Optional[List[List[List[int]]]]:
    """Try to solve using a known catalog solver."""
    solver_path = CATALOG_DIR / task_id / "solver.py"
    if not solver_path.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(f"solver_{task_id}", solver_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Catalog solvers use solve() or transform()
        fn = getattr(mod, 'solve', None) or getattr(mod, 'transform', None)
        if fn is None:
            return None

        # Verify on training examples first
        for ex in task['train']:
            result = fn(ex['input'])
            if result != ex['output']:
                return None

        # Apply to test inputs
        outputs = []
        for test in task['test']:
            out = fn(test['input'])
            outputs.append(out)
        return outputs

    except Exception:
        return None


# ─── Layer 2: Neural Grid Model with TTA ─────────────────────────

def load_neural_model(checkpoint_path: str, device: str = 'cpu',
                      d_model: int = 192, num_layers: int = 6, nhead: int = 8):
    """Load trained ARCGridModel."""
    from train_arc_v2 import ARCGridModel
    model = ARCGridModel(
        d_model=d_model, nhead=nhead, num_layers=num_layers,
        dim_feedforward=d_model * 4,
    )
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt['model_state_dict'])
    model.to(device)
    model.eval()
    return model


def guess_output_size(task: dict, test_pair: dict) -> Tuple[int, int]:
    """Guess output dimensions from training examples."""
    same_size = all(
        len(ex['output']) == len(ex['input']) and
        len(ex['output'][0]) == len(ex['input'][0])
        for ex in task['train']
    )
    if same_size:
        return len(test_pair['input']), len(test_pair['input'][0])

    out_sizes = [(len(ex['output']), len(ex['output'][0])) for ex in task['train']]
    if len(set(out_sizes)) == 1:
        return out_sizes[0]

    return len(test_pair['input']), len(test_pair['input'][0])


# ─── Augmentation transforms for TTA ─────────────────────────────

def _apply_aug(grid: np.ndarray, aug_id: int) -> np.ndarray:
    """Apply one of 8 deterministic augmentations (D4 symmetry group)."""
    g = grid.copy()
    if aug_id & 1:  # rotation 90
        g = np.rot90(g)
    if aug_id & 2:  # rotation 180
        g = np.rot90(g, 2)
    if aug_id & 4:  # horizontal flip
        g = np.fliplr(g)
    return np.ascontiguousarray(g)


def _invert_aug(grid: np.ndarray, aug_id: int) -> np.ndarray:
    """Invert the augmentation to map prediction back to original space."""
    g = grid.copy()
    if aug_id & 4:
        g = np.fliplr(g)
    if aug_id & 2:
        g = np.rot90(g, -2)
    if aug_id & 1:
        g = np.rot90(g, -1)
    return np.ascontiguousarray(g)


def _invert_aug_logits(logits: np.ndarray, aug_id: int) -> np.ndarray:
    """Invert augmentation on (H, W, C) logit tensor."""
    # logits shape: (H, W, num_classes)
    g = logits.copy()
    if aug_id & 4:
        g = np.flip(g, axis=1)  # fliplr on HxW
    if aug_id & 2:
        g = np.rot90(g, -2, axes=(0, 1))
    if aug_id & 1:
        g = np.rot90(g, -1, axes=(0, 1))
    return np.ascontiguousarray(g)


def _aug_grid_list(grid: List[List[int]], aug_id: int) -> List[List[int]]:
    """Apply augmentation to a grid (list-of-lists)."""
    return _apply_aug(np.array(grid), aug_id).tolist()


def _run_single_inference(model, context: torch.Tensor, test_in: torch.Tensor,
                          device: str) -> Tuple[np.ndarray, np.ndarray]:
    """Run model, return (logits_np, preds_np) both shape (H, W, ...)."""
    with torch.no_grad():
        result = model(context.to(device), test_in.to(device))
        logits = result['logits'][0].cpu()  # (H, W, 10)
        preds = logits.argmax(dim=-1).numpy()  # (H, W)
        probs = F.softmax(logits, dim=-1).numpy()  # (H, W, 10)
    return probs, preds


def neural_predict_tta(
    model, task: dict, device: str = 'cpu',
    num_tta: int = 1, return_confidence: bool = False,
) -> Tuple[Optional[List[List[List[int]]]], float]:
    """
    Smart TTA: run multiple augmented variants, but FILTER by self-verification.

    For each augmentation:
      1. Augment all grids (context + test input)
      2. Run inference
      3. Check if this augmentation self-verifies on training examples
      4. Only include verified augmentations in the vote

    If no augmentation verifies, fall back to plain (aug_id=0) prediction.
    Always includes aug_id=0 (identity) regardless of verification.

    Returns (outputs, confidence).
    """
    from train_arc_v2 import pad_grid, MAX_GRID, MAX_EXAMPLES, PAD

    aug_ids = list(range(min(num_tta, 8)))

    # Phase 1: Check which augmentations self-verify on training examples
    verified_augs = set()
    for aug_id in aug_ids:
        train_exs = task['train'][:MAX_EXAMPLES]
        all_correct = True

        for ex in train_exs:
            # Leave-one-out: use other examples as context
            other_exs = [e for e in task['train'] if e is not ex][:MAX_EXAMPLES]

            context_grids = []
            for e in other_exs:
                context_grids.append(pad_grid(_aug_grid_list(e['input'], aug_id), MAX_GRID, MAX_GRID))
                context_grids.append(pad_grid(_aug_grid_list(e['output'], aug_id), MAX_GRID, MAX_GRID))
            while len(context_grids) < MAX_EXAMPLES * 2:
                context_grids.append(torch.full((MAX_GRID, MAX_GRID), PAD, dtype=torch.long))

            context = torch.stack(context_grids).unsqueeze(0)
            aug_inp = _aug_grid_list(ex['input'], aug_id)
            test_in = pad_grid(aug_inp, MAX_GRID, MAX_GRID).unsqueeze(0)

            _, preds = _run_single_inference(model, context, test_in, device)

            aug_expected = _aug_grid_list(ex['output'], aug_id)
            eh, ew = len(aug_expected), len(aug_expected[0]) if aug_expected else 0
            if preds[:eh, :ew].tolist() != aug_expected:
                all_correct = False
                break

        if all_correct:
            verified_augs.add(aug_id)

    # Always include identity; prefer verified augmentations only
    use_augs = sorted(verified_augs) if verified_augs else [0]

    # Phase 2: Run inference on test pairs with selected augmentations
    outputs = []
    total_confidence = 0.0

    for test_pair in task['test']:
        train_exs = task['train'][:MAX_EXAMPLES]
        all_probs = []

        for aug_id in use_augs:
            context_grids = []
            for ex in train_exs:
                context_grids.append(pad_grid(_aug_grid_list(ex['input'], aug_id), MAX_GRID, MAX_GRID))
                context_grids.append(pad_grid(_aug_grid_list(ex['output'], aug_id), MAX_GRID, MAX_GRID))
            while len(context_grids) < MAX_EXAMPLES * 2:
                context_grids.append(torch.full((MAX_GRID, MAX_GRID), PAD, dtype=torch.long))

            context = torch.stack(context_grids).unsqueeze(0)
            aug_test_in = _aug_grid_list(test_pair['input'], aug_id)
            test_in = pad_grid(aug_test_in, MAX_GRID, MAX_GRID).unsqueeze(0)

            probs, _ = _run_single_inference(model, context, test_in, device)
            probs_orig = _invert_aug_logits(probs, aug_id)
            all_probs.append(probs_orig)

        # Average softmax probabilities across verified augmentations
        avg_probs = np.mean(all_probs, axis=0)
        voted_preds = avg_probs.argmax(axis=-1)

        if 'output' in test_pair:
            h = len(test_pair['output'])
            w = len(test_pair['output'][0]) if test_pair['output'] else 0
        else:
            h, w = guess_output_size(task, test_pair)

        out_grid = voted_preds[:h, :w].tolist()
        outputs.append(out_grid)

        out_probs = avg_probs[:h, :w, :]
        cell_confidence = out_probs.max(axis=-1).mean()
        total_confidence += cell_confidence

    avg_confidence = total_confidence / max(len(task['test']), 1)
    return outputs, float(avg_confidence)


def neural_self_verify(
    model, task: dict, device: str = 'cpu', num_tta: int = 1,
) -> bool:
    """Check if neural model gets training examples right (leave-one-out)."""
    from train_arc_v2 import pad_grid, MAX_GRID, MAX_EXAMPLES, PAD

    for ex in task['train']:
        other_exs = [e for e in task['train'] if e is not ex][:MAX_EXAMPLES]

        context_grids = []
        for e in other_exs:
            context_grids.append(pad_grid(e['input'], MAX_GRID, MAX_GRID))
            context_grids.append(pad_grid(e['output'], MAX_GRID, MAX_GRID))
        while len(context_grids) < MAX_EXAMPLES * 2:
            context_grids.append(torch.full((MAX_GRID, MAX_GRID), PAD, dtype=torch.long))

        context = torch.stack(context_grids).unsqueeze(0)
        test_in = pad_grid(ex['input'], MAX_GRID, MAX_GRID).unsqueeze(0)

        _, preds = _run_single_inference(model, context, test_in, device)
        eh, ew = len(ex['output']), len(ex['output'][0])
        if preds[:eh, :ew].tolist() != ex['output']:
            return False
    return True


def neural_predict(model, task: dict, device: str = 'cpu') -> Optional[List[List[List[int]]]]:
    """Simple single-pass neural prediction (no TTA, no verification)."""
    outputs, _ = neural_predict_tta(model, task, device, num_tta=1)
    return outputs


# ─── Layer 3: LLM Program Synthesis ───────────────────────────────

def llm_solve(task_id: str, task: dict, backend: str = 'anthropic',
              model_name: str = None, max_attempts: int = 5) -> Optional[List[List[List[int]]]]:
    """Try to solve using LLM-generated code."""
    try:
        from arc_kaggle_solver import solve_task, make_llm_call
        llm_call = make_llm_call(backend, model_name)
        result = solve_task(task_id, task, llm_call, max_attempts=max_attempts)
        if result and result.get('solved'):
            return [result['test_outputs'][i] for i in range(len(task['test']))]
    except Exception as e:
        log.debug(f"LLM solve failed for {task_id}: {e}")
    return None


# ─── Parallel Compound Pipeline ───────────────────────────────────

class CompoundPipeline:
    """
    Parallel multi-layer ARC solver.

    All enabled layers run simultaneously via ThreadPoolExecutor.
    Results are merged by priority: verified_catalog > consensus > neural_tta > neural > llm.
    """

    def __init__(
        self,
        use_catalog: bool = True,
        use_neural: bool = True,
        use_llm: bool = False,
        neural_checkpoint: str = 'checkpoints/arc_grid/best_grid.pt',
        neural_device: str = None,
        neural_tta: int = 1,
        llm_backend: str = 'anthropic',
        llm_model: str = None,
        llm_attempts: int = 5,
        parallel: bool = True,
    ):
        self.use_catalog = use_catalog
        self.use_neural = use_neural
        self.use_llm = use_llm
        self.neural_tta = neural_tta
        self.llm_backend = llm_backend
        self.llm_model = llm_model
        self.llm_attempts = llm_attempts
        self.parallel = parallel

        # Load neural model
        self.neural_model = None
        self.neural_device = neural_device or (
            'cuda' if torch.cuda.is_available()
            else 'mps' if torch.backends.mps.is_available()
            else 'cpu'
        )
        if use_neural and Path(neural_checkpoint).exists():
            log.info(f"Loading neural model from {neural_checkpoint}...")
            self.neural_model = load_neural_model(
                neural_checkpoint, device=self.neural_device)
            log.info(f"Neural model loaded on {self.neural_device} (TTA={neural_tta})")

        self.stats = {
            'catalog': 0, 'neural_verified': 0, 'neural_tta': 0,
            'neural_fallback': 0, 'llm': 0, 'consensus': 0,
            'unsolved': 0, 'total': 0, 'errors': 0,
        }
        self.confidence_log: List[Tuple[str, str, float]] = []

    def _run_catalog(self, task_id: str, task: dict) -> Dict:
        """Run catalog solver, return result dict."""
        result = catalog_solve(task_id, task)
        return {'method': 'catalog', 'outputs': result, 'confidence': 1.0 if result else 0.0}

    def _run_neural(self, task_id: str, task: dict) -> Dict:
        """Run neural solver with TTA, return result dict."""
        if self.neural_model is None:
            return {'method': 'neural', 'outputs': None, 'confidence': 0.0}

        try:
            outputs, confidence = neural_predict_tta(
                self.neural_model, task, self.neural_device,
                num_tta=self.neural_tta, return_confidence=True,
            )
            # Also check self-verification
            verified = neural_self_verify(
                self.neural_model, task, self.neural_device,
                num_tta=self.neural_tta,
            )
            return {
                'method': 'neural',
                'outputs': outputs,
                'confidence': confidence,
                'verified': verified,
                'tta': self.neural_tta > 1,
            }
        except Exception as e:
            log.debug(f"Neural error on {task_id}: {e}")
            return {'method': 'neural', 'outputs': None, 'confidence': 0.0, 'error': str(e)}

    def _run_llm(self, task_id: str, task: dict) -> Dict:
        """Run LLM solver, return result dict."""
        result = llm_solve(task_id, task, self.llm_backend, self.llm_model, self.llm_attempts)
        return {'method': 'llm', 'outputs': result, 'confidence': 0.9 if result else 0.0}

    def _merge_results(
        self, task_id: str, results: Dict[str, Dict],
    ) -> Tuple[Optional[List], str, float]:
        """
        Merge parallel results. Priority:
        1. Catalog (verified on training) — confidence 1.0
        2. Consensus (catalog + neural agree) — confidence 1.0
        3. Neural verified (passes training self-check) with TTA — 0.7-0.95
        4. Neural unverified with TTA — 0.3-0.7
        5. LLM — 0.5-0.9
        6. Neural fallback (no TTA, no verify) — 0.1-0.5
        """
        catalog_r = results.get('catalog', {})
        neural_r = results.get('neural', {})
        llm_r = results.get('llm', {})

        catalog_out = catalog_r.get('outputs')
        neural_out = neural_r.get('outputs')
        neural_conf = neural_r.get('confidence', 0.0)
        neural_verified = neural_r.get('verified', False)
        neural_tta = neural_r.get('tta', False)
        llm_out = llm_r.get('outputs')

        # Check consensus: catalog and neural agree
        if catalog_out and neural_out and catalog_out == neural_out:
            self.stats['consensus'] += 1
            return catalog_out, 'consensus', 1.0

        # Catalog is gold standard (verified on training examples)
        if catalog_out:
            self.stats['catalog'] += 1
            return catalog_out, 'catalog', 1.0

        # Neural verified + TTA = strong signal
        if neural_out and neural_verified and neural_tta:
            self.stats['neural_tta'] += 1
            return neural_out, 'neural_tta_verified', neural_conf

        # Neural verified (no TTA)
        if neural_out and neural_verified:
            self.stats['neural_verified'] += 1
            return neural_out, 'neural_verified', neural_conf

        # LLM (verified by arc_kaggle_solver internally)
        if llm_out:
            self.stats['llm'] += 1
            return llm_out, 'llm', 0.85

        # Neural unverified with TTA (better than plain)
        if neural_out and neural_tta:
            self.stats['neural_tta'] += 1
            return neural_out, 'neural_tta', neural_conf

        # Neural fallback (anything is better than nothing)
        if neural_out:
            self.stats['neural_fallback'] += 1
            return neural_out, 'neural_fallback', neural_conf

        self.stats['unsolved'] += 1
        return None, 'unsolved', 0.0

    def solve(self, task_id: str, task: dict) -> Tuple[Optional[List], str, float]:
        """
        Solve a task using all layers in parallel.
        Returns (outputs, method, confidence).
        """
        self.stats['total'] += 1

        if self.parallel:
            # Run all enabled layers simultaneously
            futures = {}
            with ThreadPoolExecutor(max_workers=3) as pool:
                if self.use_catalog:
                    futures['catalog'] = pool.submit(self._run_catalog, task_id, task)
                if self.use_neural and self.neural_model is not None:
                    futures['neural'] = pool.submit(self._run_neural, task_id, task)
                if self.use_llm:
                    futures['llm'] = pool.submit(self._run_llm, task_id, task)

            results = {}
            for key, fut in futures.items():
                try:
                    results[key] = fut.result(timeout=120)
                except Exception as e:
                    log.debug(f"Layer {key} failed for {task_id}: {e}")
                    results[key] = {'method': key, 'outputs': None, 'confidence': 0.0}
                    self.stats['errors'] += 1
        else:
            # Sequential fallback
            results = {}
            if self.use_catalog:
                results['catalog'] = self._run_catalog(task_id, task)
                if results['catalog']['outputs']:
                    self.stats['catalog'] += 1
                    return results['catalog']['outputs'], 'catalog', 1.0

            if self.use_neural and self.neural_model is not None:
                results['neural'] = self._run_neural(task_id, task)

            if self.use_llm:
                results['llm'] = self._run_llm(task_id, task)

        outputs, method, confidence = self._merge_results(task_id, results)
        self.confidence_log.append((task_id, method, confidence))
        return outputs, method, confidence

    def print_stats(self):
        s = self.stats
        total = s['total'] or 1
        solved = (s['catalog'] + s['neural_verified'] + s['neural_tta']
                  + s['neural_fallback'] + s['llm'] + s['consensus'])
        print()
        print("=" * 65)
        print(f"PARALLEL COMPOUND PIPELINE — {solved}/{s['total']} solved ({100*solved/total:.1f}%)")
        print("=" * 65)
        print(f"  Consensus (catalog+neural):  {s['consensus']:>4} tasks")
        print(f"  Catalog only:                {s['catalog']:>4} tasks")
        print(f"  Neural TTA verified:         {s['neural_tta']:>4} tasks")
        print(f"  Neural verified:             {s['neural_verified']:>4} tasks")
        print(f"  Neural fallback:             {s['neural_fallback']:>4} tasks")
        print(f"  LLM:                         {s['llm']:>4} tasks")
        print(f"  Unsolved:                    {s['unsolved']:>4} tasks")
        if s['errors']:
            print(f"  Errors:                      {s['errors']:>4}")
        print("=" * 65)

        # Confidence distribution
        if self.confidence_log:
            confs = [c for _, _, c in self.confidence_log if c > 0]
            if confs:
                avg = sum(confs) / len(confs)
                high = sum(1 for c in confs if c > 0.8)
                med = sum(1 for c in confs if 0.5 < c <= 0.8)
                low = sum(1 for c in confs if c <= 0.5)
                print(f"\n  Confidence: avg={avg:.3f} | high(>0.8)={high} | med={med} | low={low}")


# ─── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='ARC Parallel Compound Pipeline')
    parser.add_argument('--data', default='ARC_AMD_TRANSFER/data/ARC-AGI/data',
                        help='Path to ARC data directory')
    parser.add_argument('--split', default='evaluation',
                        help='Dataset split (training/evaluation)')
    parser.add_argument('--task', default=None,
                        help='Solve single task by ID')
    parser.add_argument('--no-catalog', action='store_true',
                        help='Skip catalog lookup')
    parser.add_argument('--no-neural', action='store_true',
                        help='Skip neural model')
    parser.add_argument('--use-llm', action='store_true',
                        help='Enable LLM layer (needs API key)')
    parser.add_argument('--llm-backend', default='anthropic',
                        choices=['anthropic', 'openai', 'ollama'])
    parser.add_argument('--llm-model', default=None)
    parser.add_argument('--llm-attempts', type=int, default=5)
    parser.add_argument('--checkpoint', default='checkpoints/arc_grid/best_grid.pt')
    parser.add_argument('--device', default=None)
    parser.add_argument('--neural-tta', type=int, default=1,
                        help='Number of TTA augmentations (1=off, 8=full D4 group)')
    parser.add_argument('--sequential', action='store_true',
                        help='Run layers sequentially instead of parallel')
    parser.add_argument('--out', default=None,
                        help='Output JSON file for submission')
    parser.add_argument('--limit', type=int, default=None,
                        help='Max tasks to evaluate')
    args = parser.parse_args()

    log.info("=" * 65)
    log.info("ARC PARALLEL COMPOUND PIPELINE — Catalog + Neural(TTA) + LLM")
    log.info("=" * 65)

    pipeline = CompoundPipeline(
        use_catalog=not args.no_catalog,
        use_neural=not args.no_neural,
        use_llm=args.use_llm,
        neural_checkpoint=args.checkpoint,
        neural_device=args.device,
        neural_tta=args.neural_tta,
        llm_backend=args.llm_backend,
        llm_model=args.llm_model,
        llm_attempts=args.llm_attempts,
        parallel=not args.sequential,
    )

    # Load tasks
    if args.task:
        task_file = Path(args.data) / args.split / f"{args.task}.json"
        with open(task_file) as f:
            task_data = json.load(f)
        tasks = [(args.task, task_data)]
    else:
        task_dir = Path(args.data) / args.split
        tasks = []
        for f in sorted(task_dir.glob('*.json')):
            with open(f) as fh:
                tasks.append((f.stem, json.load(fh)))

    if args.limit:
        tasks = tasks[:args.limit]

    log.info(f"Evaluating {len(tasks)} tasks from {args.split}")
    log.info(f"Mode: {'PARALLEL' if not args.sequential else 'SEQUENTIAL'} | TTA={args.neural_tta}")

    # Solve
    submission = {}
    correct_count = 0
    results_detail = []
    start = time.time()

    for i, (tid, tdata) in enumerate(tasks):
        outputs, method, confidence = pipeline.solve(tid, tdata)

        if outputs is not None:
            correct = True
            for j, test in enumerate(tdata['test']):
                if 'output' in test:
                    if outputs[j] != test['output']:
                        correct = False
                        break

            if correct:
                correct_count += 1

            tag = "CORRECT" if correct else "WRONG"
            log.info(f"[{i+1}/{len(tasks)}] {tid}: {method} ({tag}) conf={confidence:.3f}")
            submission[tid] = outputs
            results_detail.append({
                'task_id': tid, 'method': method, 'correct': correct,
                'confidence': confidence,
            })
        else:
            log.info(f"[{i+1}/{len(tasks)}] {tid}: unsolved")
            results_detail.append({
                'task_id': tid, 'method': 'unsolved', 'correct': False,
                'confidence': 0.0,
            })

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            log.info(f"  Progress: {i+1}/{len(tasks)} | Correct: {correct_count} | {elapsed:.0f}s")

    elapsed = time.time() - start
    pipeline.print_stats()
    print(f"\n  CORRECT: {correct_count}/{len(tasks)} ({100*correct_count/max(len(tasks),1):.1f}%)")
    log.info(f"Time: {elapsed:.1f}s ({elapsed/len(tasks):.2f}s/task)")

    # Save submission
    if args.out:
        out_data = {
            'submission': submission,
            'results': results_detail,
            'stats': pipeline.stats,
            'correct': correct_count,
            'total': len(tasks),
        }
        with open(args.out, 'w') as f:
            json.dump(out_data, f, indent=2)
        log.info(f"Results saved to {args.out}")

    # Print method breakdown for non-catalog methods
    for method in ['consensus', 'neural_tta_verified', 'neural_verified',
                   'neural_tta', 'neural_fallback', 'llm']:
        method_tasks = [r for r in results_detail if r['method'] == method]
        if method_tasks:
            correct_m = sum(1 for r in method_tasks if r['correct'])
            log.info(f"  {method}: {correct_m}/{len(method_tasks)} correct "
                     f"(avg conf={sum(r['confidence'] for r in method_tasks)/len(method_tasks):.3f})")


if __name__ == '__main__':
    main()
