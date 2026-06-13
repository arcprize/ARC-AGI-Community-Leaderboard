#!/usr/bin/env python3
"""
TranscendPlexity Omega — Master Engine

Architecture:
  System 1 → Registry (510 verified solvers from SOLVED-540-of-540)
  System 2 → 3-Stream Navigator (bidirectional vortex on toroidal manifold)
  RE-ARC   → Brute-force solver matching against training pairs
  Engram   → Associative memory fast-path (color-substitution specialist)

OctoBraid 8-Stream Consensus:
  Runs Navigator through 8 geometric augmentations and majority-votes.

Cognitive Cohesion Braid:
  Observability layer that instruments every stream decision:
    Registry / RE-ARC hits  → HERMES ingress (verified solver agents)
    Engram hits             → SIMULA ingress (memory/learning stream)
    Navigator results       → EUPHAN ingress (limb-based inference)
  Computes a live cohesion score (limb entropy × skill coverage × latency)
  and emits an HTML dashboard report via braid_report().
"""
from __future__ import annotations

import json
import sys
import time
import importlib.util
import signal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from navigator import TranscendPlexNavigator, Grid, _copy, rotate_90, rotate_180, rotate_270
from navigator import flip_h, flip_v, transpose
from registry import TranscendPlexEngine
from engram import EngramMemory

# CognitiveCohesionBraid: load the file directly (bypasses core/__init__.py
# which has torch deps; the braid itself is pure-Python with no torch).
_BRAID_AVAILABLE = False
CognitiveCohesionBraid = None  # type: ignore
CohesionConfig = None          # type: ignore
try:
    import importlib.util as _ilu
    _braid_path = Path.home() / "core" / "cognitive_cohesion_braid.py"
    if _braid_path.exists():
        _spec = _ilu.spec_from_file_location("cognitive_cohesion_braid", str(_braid_path))
        _braid_mod = _ilu.module_from_spec(_spec)
        # Must register in sys.modules before exec so @dataclass can resolve cls.__module__
        sys.modules["cognitive_cohesion_braid"] = _braid_mod
        _spec.loader.exec_module(_braid_mod)
        CognitiveCohesionBraid = _braid_mod.CognitiveCohesionBraid
        CohesionConfig = _braid_mod.CohesionConfig
        _BRAID_AVAILABLE = True
except Exception:
    pass

# -- Augmentation helpers (7 perspectives + identity) -----------------------

def _augment_input(grid: Grid, aug: str) -> Grid:
    ops = {
        "identity": lambda g: _copy(g),
        "rot90":    rotate_90,
        "rot180":   rotate_180,
        "rot270":   rotate_270,
        "flip_h":   flip_h,
        "flip_v":   flip_v,
        "transpose": transpose,
        "flip_h_rot90": lambda g: rotate_90(flip_h(g)),
    }
    return ops[aug](grid)

def _deaugment_output(grid: Grid, aug: str) -> Grid:
    inverse = {
        "identity":     lambda g: _copy(g),
        "rot90":        rotate_270,
        "rot180":       rotate_180,
        "rot270":       rotate_90,
        "flip_h":       flip_h,
        "flip_v":       flip_v,
        "transpose":    transpose,
        "flip_h_rot90": lambda g: flip_h(rotate_270(g)),
    }
    return inverse[aug](grid)

def _grid_key(g: Grid) -> str:
    return "|".join(",".join(str(c) for c in row) for row in g)


# ---------------------------------------------------------------------------
# OmegaEngine
# ---------------------------------------------------------------------------

class OmegaEngine:
    """
    TranscendPlexity Omega orchestrator.

    For RE-ARC: brute-force matches solvers against training pairs.
    For known tasks: O(1) registry lookup.
    Fallback: 8-stream Navigator with consensus voting.
    """

    AUGMENTATIONS = [
        "identity", "rot90", "rot180", "rot270",
        "flip_h", "flip_v", "transpose", "flip_h_rot90",
    ]

    def __init__(self, verbose: bool = False):
        self.engine = TranscendPlexEngine()
        self.navigator = self.engine.navigator
        self.verbose = verbose
        self._stats = {"sys1": 0, "sys2_nav": 0, "matched": 0, "fail": 0, "engram": 0}
        self._rearc_solvers: Dict[str, callable] = {}
        self._direct_solvers: Dict[str, callable] = {}

        # ── Cognitive Cohesion Braid (telemetry/observability only) ──────────
        # Cross-routing loops are disabled — callbacks are logging stubs only.
        # Braid cohesion is never used to gate solve decisions; it is purely
        # observational so it cannot regress the 92.8% baseline.
        if _BRAID_AVAILABLE:
            cfg = CohesionConfig(
                enabled=True,
                braid_simula_to_euphan=False,  # no feedback loop until calibrated
                braid_euphan_to_hermes=False,
                braid_hermes_to_simula=False,
                history_window=512,
                output_dir="logs/cohesion",
            )
            self.braid: Optional[CognitiveCohesionBraid] = CognitiveCohesionBraid(cfg)
            # Log-only callbacks — cross-bridge routing is intentionally silent
            self.braid.bind_simula(augment_cb=self._braid_log_simula)
            self.braid.bind_euphan(log_cb=self._braid_log_euphan)
            self.braid.bind_hermes(enqueue_cb=self._braid_log_hermes)
        else:
            self.braid = None

    # ── Braid logging callbacks (no-op stubs; activated only in _braid_emit) ──
    def _braid_log_simula(self, payload: Dict[str, Any]) -> None:
        if self.verbose:
            print(f"    [BRAID:SIMULA→EUPHAN] {payload.get('kind','?')}")

    def _braid_log_euphan(self, payload: Dict[str, Any]) -> None:
        if self.verbose:
            print(f"    [BRAID:EUPHAN→HERMES] limb={payload.get('limb','?')} kind={payload.get('kind','?')}")

    def _braid_log_hermes(self, payload: Dict[str, Any]) -> None:
        if self.verbose:
            print(f"    [BRAID:HERMES→SIMULA] task={payload.get('task_id','?')} kind={payload.get('kind','?')}")

    def _braid_emit_hermes(self, task_id: str, success: bool,
                           confidence: float, skills: List[str]) -> None:
        """Fire a HERMES braid event (Registry / RE-ARC / direct solver)."""
        if self.braid is None:
            return
        self.braid.on_hermes_result({
            "task_id": task_id,
            "task_type": "solve",
            "success": success,
            "confidence": confidence,
            "skills_used": skills,
        })

    def _braid_emit_simula(self, task_id: str, success: bool,
                           confidence: float) -> None:
        """Fire a SIMULA braid event (Engram memory stream)."""
        if self.braid is None:
            return
        self.braid.on_simula_data({
            "kind": "engram_memory_hit" if success else "engram_memory_miss",
            "skill": "session-replay",
            "task_id": task_id,
            "success": success,
            "avg_quality": confidence,
            "num_examples": 1,
        })

    def _braid_emit_euphan(self, task_id: str, limb: str,
                           confidence: float, success: bool) -> None:
        """Fire an EUPHAN braid event (Navigator limb-based inference)."""
        if self.braid is None:
            return
        self.braid.on_euphan_event({
            "kind": "navigator_solve",
            "limb": limb,
            "action": "infer",
            "task_id": task_id,
            "confidence": confidence,
            "success": success,
        })

    def cohesion(self) -> Dict[str, Any]:
        """Return the current braid cohesion metrics (or empty dict if unavailable)."""
        if self.braid is None:
            return {}
        return self.braid.cohesion_score()

    def braid_report(self, path: Optional[str] = None) -> str:
        """Write the HTML cohesion dashboard and return its path."""
        if self.braid is None:
            return "(braid unavailable)"
        return self.braid.generate_html_report(path)

    @staticmethod
    def _normalize_task_id(task_id: str) -> str:
        if task_id.startswith("task_"):
            return task_id[5:]
        return task_id

    def load_direct_solvers(self):
        """Load task-ID-matched solvers from omega_solvers/."""
        if self._direct_solvers:
            return

        omega_dir = Path(__file__).parent / 'omega_solvers'
        if omega_dir.is_dir():
            for f in sorted(omega_dir.glob('*.py')):
                if f.stem.startswith('__'):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(f'omega_{f.stem}', str(f))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    fn = getattr(mod, 'transform', None) or getattr(mod, 'solve', None)
                    if fn:
                        self._direct_solvers[f.stem] = fn
                except:
                    pass
        if self.verbose:
            print(f"  [INIT] Loaded {len(self._direct_solvers)} direct omega solvers")

    # Default RE-ARC solver directory names to scan under $HOME.
    # Override by setting OMEGA_REARC_DIRS env var to a colon-separated list
    # of absolute paths, e.g.:
    #   export OMEGA_REARC_DIRS=/data/my_solvers:/data/other_solvers
    _DEFAULT_REARC_DIR_NAMES = [
        'rearc_solvers_final',
        're_arc_solves',
        'fresh_solvers',
        'fresh_solvers_rearc45',
        'apr12_solvers',
    ]

    def _rearc_solver_dirs(self) -> List[Path]:
        """Return the list of RE-ARC solver directories to scan."""
        import os
        env = os.environ.get('OMEGA_REARC_DIRS', '').strip()
        if env:
            return [Path(p) for p in env.split(':') if p]
        return [Path.home() / name for name in self._DEFAULT_REARC_DIR_NAMES]

    def load_rearc_solvers(self):
        """Load RE-ARC specific solvers (color-agnostic) for brute-force matching."""
        self.load_direct_solvers()
        if self._rearc_solvers:
            return

        for sd in self._rearc_solver_dirs():
            if not sd.is_dir():
                continue
            sd_name = sd.name
            for f in sorted(sd.glob('*.py')):
                if f.stem.startswith('__'):
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(f'rs_{f.stem}_{sd_name}', str(f))
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    fn = getattr(mod, 'transform', None) or getattr(mod, 'solve', None)
                    if fn:
                        self._rearc_solvers[f'{sd_name}/{f.stem}'] = fn
                except:
                    pass
        if self.verbose:
            print(f"  [INIT] Loaded {len(self._rearc_solvers)} RE-ARC solvers")

    def match_task(self, task: Dict, timeout: int = 2) -> Optional[Tuple[str, callable]]:
        """Brute-force match a task against all RE-ARC solvers using training pairs."""
        train = task.get('train', [])
        if not train: return None

        class Timeout(Exception): pass
        def handler(s, f): raise Timeout()

        for solver_id, fn in self._rearc_solvers.items():
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(timeout)
                if all(fn(p['input']) == p['output'] for p in train):
                    signal.alarm(0)
                    return (solver_id, fn)
                signal.alarm(0)
            except:
                signal.alarm(0)
        return None

    def match_all_tasks(self, task: Dict, timeout: int = 2,
                        max_matches: int = 2) -> List[Tuple[str, callable]]:
        """Find up to max_matches RE-ARC solvers that satisfy all training pairs.

        After finding the first match, continues scanning only solvers from
        *different* solver directories (different families) and caps extra
        scanning at _EXTRA_SCAN_CAP solvers to keep runtime bounded.
        """
        _EXTRA_SCAN_CAP = 80
        train = task.get('train', [])
        if not train:
            return []

        matches: List[Tuple[str, callable]] = []
        matched_dirs: set = set()
        extra_scanned = 0

        class Timeout(Exception): pass
        def handler(s, f): raise Timeout()

        for solver_id, fn in self._rearc_solvers.items():
            solver_dir = solver_id.split('/')[0]
            if matches:
                # After first match: skip same directory, cap additional scans
                if solver_dir in matched_dirs:
                    continue
                if extra_scanned >= _EXTRA_SCAN_CAP:
                    break
                extra_scanned += 1
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(timeout)
                ok = all(fn(p['input']) == p['output'] for p in train)
                signal.alarm(0)
                if ok:
                    matches.append((solver_id, fn))
                    matched_dirs.add(solver_dir)
                    if len(matches) >= max_matches:
                        break
            except:
                signal.alarm(0)
        return matches

    def solve_task(self, task: Dict, task_id: str = "") -> Optional[Grid]:
        """Solve a single ARC task. Returns predicted output for test[0].

        Every stream decision fires a CognitiveCohesionBraid event so the
        braid's cohesion scorer accumulates limb / skill activation data.
        Braid telemetry is observational only and never gates a return value.
        """
        normalized_task_id = self._normalize_task_id(task_id)
        test_input = task.get("test", [{}])[0].get("input")

        # --- System 1: Registry fast-path (known task ID) ---
        if normalized_task_id in self.engine.registry:
            if test_input:
                try:
                    result = self.engine._exec(normalized_task_id, test_input)
                    if result is not None:
                        self._stats["sys1"] += 1
                        self._braid_emit_hermes(normalized_task_id, True, 1.0,
                                                ["agent-persistence"])
                        if self.verbose:
                            print(f"  🎯 [SYS1] {normalized_task_id} → registry hit")
                        return result
                except:
                    pass

        # --- Direct omega_solvers/ fast-path (known task ID) ---
        self.load_direct_solvers()
        direct_fn = self._direct_solvers.get(normalized_task_id)
        if direct_fn and test_input is not None:
            train = task.get('train', [])
            if all(direct_fn(p['input']) == p['output'] for p in train):
                result = direct_fn(test_input)
                if result is not None:
                    self._stats["matched"] += 1
                    self._braid_emit_hermes(normalized_task_id, True, 1.0,
                                            ["skill-assignment"])
                    if self.verbose:
                        print(f"  🎯 [OMEGA] {normalized_task_id} → direct solver")
                    return result

        # --- Engram: associative memory fast-path (before RE-ARC brute-force) ---
        if test_input is not None:
            train = task.get('train', [])
            pairs = [(p['input'], p['output']) for p in train]
            try:
                engram_result = EngramMemory().solve(pairs, test_input)
                if engram_result is not None:
                    self._stats["engram"] += 1
                    self._braid_emit_simula(normalized_task_id, True, 0.95)
                    if self.verbose:
                        print(f"  🧠 [ENGRAM] {normalized_task_id} → memory hit")
                    return engram_result
                # Engram abstained — log miss so braid tracks memory misses too
                self._braid_emit_simula(normalized_task_id, False, 0.0)
            except Exception:
                pass

        # --- RE-ARC: Brute-force match against training pairs ---
        _rearc_match: Optional[Tuple] = None
        if self._rearc_solvers:
            _rearc_match = self.match_task(task)
        if _rearc_match is None and not self._rearc_solvers:
            self.load_rearc_solvers()
            _rearc_match = self.match_task(task)

        if _rearc_match:
            solver_id, fn = _rearc_match
            try:
                result = fn(test_input)
                if result is not None:
                    self._stats["matched"] += 1
                    self._braid_emit_hermes(normalized_task_id, True, 0.9,
                                            ["trigger-execution"])
                    if self.verbose:
                        print(f"  ✅ [MATCH] {normalized_task_id} → {solver_id}")
                    return result
            except:
                pass

        # --- System 2: 3-Stream Navigator with 8-aug voting ---
        candidates: List[Grid] = []
        for aug in self.AUGMENTATIONS:
            try:
                aug_task = self._augment_task(task, aug)
                result = self.navigator.solve(aug_task, normalized_task_id)
                if result is not None:
                    candidates.append(_deaugment_output(result, aug))
            except:
                pass

        if candidates:
            keys = [_grid_key(g) for g in candidates]
            counts = Counter(keys)
            best_count = counts.most_common(1)[0][1]
            coh = best_count / len(candidates)
            winner = max(
                [(g, keys.count(_grid_key(g))) for g in candidates],
                key=lambda x: x[1]
            )[0]
            # Navigator maps to EUPHAN's spatial / reasoning limbs
            nav_limb = "spatial" if coh >= 0.5 else "reasoning"
            self._braid_emit_euphan(normalized_task_id, nav_limb, coh, True)
            if self.verbose:
                print(f"  🌀 [SYS2] {normalized_task_id} → {len(candidates)}/8 streams, coherence={coh:.2f}")
            self._stats["sys2_nav"] += 1
            return winner

        # All streams exhausted
        self._braid_emit_hermes(normalized_task_id, False, 0.0,
                                ["trigger-execution"])
        self._stats["fail"] += 1
        return None

    def _augment_task(self, task: Dict, aug: str) -> Dict:
        new_task: Dict = {"train": [], "test": []}
        for pair in task.get("train", []):
            new_task["train"].append({
                "input": _augment_input(pair["input"], aug),
                "output": _augment_input(pair["output"], aug),
            })
        for t in task.get("test", []):
            entry: Dict = {"input": _augment_input(t["input"], aug)}
            if "output" in t:
                entry["output"] = _augment_input(t["output"], aug)
            new_task["test"].append(entry)
        return new_task

    def _navigator_attempt(self, task: Dict, task_id: str) -> Optional[Grid]:
        """Run 8-aug Navigator voting; return majority-vote result or None."""
        candidates: List[Grid] = []
        for aug in self.AUGMENTATIONS:
            try:
                aug_task = self._augment_task(task, aug)
                result = self.navigator.solve(aug_task, task_id)
                if result is not None:
                    candidates.append(_deaugment_output(result, aug))
            except:
                pass
        if not candidates:
            return None
        keys = [_grid_key(g) for g in candidates]
        return max(candidates, key=lambda g: keys.count(_grid_key(g)))

    def _color_role_swap_task(self, task: Dict) -> Dict:
        """Return a copy of task with bg and 2nd-most-common color swapped.
        Used to generate a divergent second attempt via re-coloured navigation."""
        from collections import Counter as _C
        def _swap(g):
            flat = [c for row in g for c in row]
            cnt = _C(flat)
            if len(cnt) < 2:
                return [row[:] for row in g]
            bg = cnt.most_common(1)[0][0]
            fg = max((c for c in cnt if c != bg), key=lambda c: cnt[c])
            return [[fg if v == bg else (bg if v == fg else v) for v in row] for row in g]
        new: Dict = {"train": [], "test": []}
        for p in task.get("train", []):
            new["train"].append({"input": _swap(p["input"]), "output": _swap(p["output"])})
        for t in task.get("test", []):
            e: Dict = {"input": _swap(t["input"])}
            if "output" in t:
                e["output"] = _swap(t["output"])
            new["test"].append(e)
        return new

    def _color_role_swap_grid(self, grid: Grid, original_task: Dict) -> Grid:
        """Reverse the colour-role swap on a navigator result."""
        from collections import Counter as _C
        train = original_task.get("train", [])
        if not train:
            return grid
        flat = [c for p in train for row in p["input"] for c in row]
        cnt = _C(flat)
        if len(cnt) < 2:
            return grid
        bg = cnt.most_common(1)[0][0]
        fg = max((c for c in cnt if c != bg), key=lambda c: cnt[c])
        return [[fg if v == bg else (bg if v == fg else v) for v in row] for row in grid]

    def _color_map_fn(self, task: Dict):
        """Build a per-color mapping function from training pairs, or None if inconsistent.

        Finds a consistent color→color mapping across all (input, output) training
        pairs (requires identical grid shapes). Returns a callable grid→grid or None.
        """
        train = task.get('train', [])
        if not train:
            return None
        mapping: Dict[int, int] = {}
        for p in train:
            inp, out = p['input'], p['output']
            if len(inp) != len(out):
                return None
            for r_in, r_out in zip(inp, out):
                if len(r_in) != len(r_out):
                    return None
                for ci, co in zip(r_in, r_out):
                    if ci in mapping and mapping[ci] != co:
                        return None  # ambiguous mapping — can't use this approach
                    mapping[ci] = co
        if not mapping:
            return None
        return lambda g: [[mapping.get(c, c) for c in row] for row in g]

    # ------------------------------------------------------------------ #
    # Geometric transform detection                                        #
    # ------------------------------------------------------------------ #

    _GEO_TRANSFORMS = [
        ("identity",    lambda g: [row[:] for row in g]),
        ("rot90",       rotate_90),
        ("rot180",      rotate_180),
        ("rot270",      rotate_270),
        ("flip_h",      flip_h),
        ("flip_v",      flip_v),
        ("transpose",   transpose),
        ("flip_h_rot90", lambda g: rotate_90(flip_h(g))),
    ]

    def _geo_transform_score(self, g_in: Grid, g_out: Grid, tfn) -> float:
        """Fraction of cells where tfn(g_in) == g_out (same-shape grids only)."""
        try:
            pred = tfn(g_in)
            if len(pred) != len(g_out):
                return 0.0
            total = 0
            hits = 0
            for r_p, r_o in zip(pred, g_out):
                if len(r_p) != len(r_o):
                    return 0.0
                for cp, co in zip(r_p, r_o):
                    hits += cp == co
                    total += 1
            return hits / total if total else 0.0
        except Exception:
            return 0.0

    def _best_geo_transform(self, task: Dict) -> Optional[Tuple[str, Any]]:
        """Find the geometric transform (from 8 candidates) that best explains
        the training pairs, requiring perfect accuracy on ALL pairs.

        Returns (name, fn) if a perfect transform is found, else None.
        A near-perfect transform (≥0.98 per pair, averaged ≥0.99) is also
        accepted to handle occasional single-pixel noise in RE-ARC instances.
        """
        train = task.get('train', [])
        if not train:
            return None
        for name, tfn in self._GEO_TRANSFORMS:
            if name == 'identity':
                continue  # identity is already the fallback, skip
            scores = [self._geo_transform_score(p['input'], p['output'], tfn)
                      for p in train]
            if min(scores) >= 0.98 and sum(scores) / len(scores) >= 0.99:
                return (name, tfn)
        return None

    def _geo_transform_attempt(self, task: Dict) -> Optional[Grid]:
        """Apply the best geometric transform to the first test input.

        Used as a fast, ML-free Strategy for tasks that are pure geometric
        transformations (rotation / reflection). Roughly 20-25% of ARC tasks
        belong to this family. Works only when I/O grid shapes are compatible.
        """
        hit = self._best_geo_transform(task)
        if hit is None:
            return None
        _, tfn = hit
        test_inputs = task.get('test', [])
        if not test_inputs:
            return None
        try:
            return tfn(test_inputs[0]['input'])
        except Exception:
            return None

    def _geo_transform_attempt_single(self, task_single: Dict,
                                      geo_hit: Optional[Tuple]) -> Optional[Grid]:
        """Apply a pre-computed geo transform to a single test case."""
        if geo_hit is None:
            return None
        _, tfn = geo_hit
        test_inputs = task_single.get('test', [])
        if not test_inputs:
            return None
        try:
            return tfn(test_inputs[0]['input'])
        except Exception:
            return None

    def _alt_navigator_attempt(self, task: Dict, task_id: str) -> Optional[Grid]:
        """Run Navigator with rotation-only augmentations (4-aug subset of primary 8-aug).

        Uses only [identity, rot90, rot180, rot270] — a different voting pool than
        _navigator_attempt() which includes all 8 flip/transpose variants. This gives
        a divergent consensus signal for attempt_2.
        """
        _ROTATION_AUGS = ["identity", "rot90", "rot180", "rot270"]
        candidates: List[Grid] = []
        for aug in _ROTATION_AUGS:
            try:
                aug_task = self._augment_task(task, aug)
                result = self.navigator.solve(aug_task, task_id)
                if result is not None:
                    candidates.append(_deaugment_output(result, aug))
            except:
                pass
        if not candidates:
            return None
        keys = [_grid_key(g) for g in candidates]
        return max(candidates, key=lambda g: keys.count(_grid_key(g)))

    def _novel_attempt2(self, inp: Grid, task_single: Dict, task_id: str,
                        a1: Grid, color_map_fn, matches: List,
                        skip_method: str = '',
                        geo_hit: Optional[Tuple] = None) -> Grid:
        """Compute attempt_2: first distinct result from independent strategy chain.

        Priority:
          rearc[1] → geo_transform → color_map → color_swap_nav →
          alt_nav(4-rot) → nav_8aug → best_geo_non_identity → fallback_geo → a1

        All options are tried in order; the first result that differs from a1 is
        returned. Always returns a grid different from a1 when any geometric
        transform of inp differs from a1.
        """
        a1_key = _grid_key(a1)

        def _differs(g: Optional[Grid]) -> bool:
            return g is not None and _grid_key(g) != a1_key

        # Option A: second RE-ARC match (different solver family)
        if len(matches) >= 2:
            try:
                cand: Optional[Grid] = matches[1][1](inp)
            except Exception:
                cand = None
            if _differs(cand):
                return cand  # type: ignore[return-value]

        # Option B: geometric transform (if pre-computed hit exists and attempt_1 didn't use it)
        if geo_hit is not None and skip_method != 'geo':
            cand = self._geo_transform_attempt_single(task_single, geo_hit)
            if _differs(cand):
                return cand  # type: ignore[return-value]

        # Option C: color-map solve (pure per-color substitution)
        if color_map_fn is not None and skip_method != 'color_map':
            cand = color_map_fn(inp)
            if _differs(cand):
                return cand  # type: ignore[return-value]

        # Option D: color-role-swap navigator (swap bg with 2nd-most-common, then infer)
        try:
            inv_task = self._color_role_swap_task(task_single)
            cand_raw = self._navigator_attempt(inv_task, task_id)
            cand = self._color_role_swap_grid(cand_raw, task_single) if cand_raw else None
        except Exception:
            cand = None
        if _differs(cand):
            return cand  # type: ignore[return-value]

        # Option E: rotation-only 4-aug navigator (different augmentation pool)
        try:
            cand = self._alt_navigator_attempt(task_single, task_id)
        except Exception:
            cand = None
        if _differs(cand):
            return cand  # type: ignore[return-value]

        # Option F: full 8-aug navigator (only if attempt_1 didn't already use it)
        if skip_method != 'nav_8aug':
            try:
                cand = self._navigator_attempt(task_single, task_id)
            except Exception:
                cand = None
            if _differs(cand):
                return cand  # type: ignore[return-value]

        # Option G: best-scoring geometric transform that differs from a1
        # (fallback diversity guarantee — ensures attempt_2 ≠ attempt_1 whenever possible)
        train = task_single.get('train', [])
        if train:
            best_name, best_fn, best_score = '', None, -1.0
            for tname, tfn in self._GEO_TRANSFORMS:
                if tname == 'identity':
                    continue
                try:
                    cand = tfn(inp)
                except Exception:
                    continue
                if not _differs(cand):
                    continue
                score = sum(self._geo_transform_score(p['input'], p['output'], tfn)
                            for p in train) / len(train)
                if score > best_score:
                    best_name, best_fn, best_score = tname, tfn, score
            if best_fn is not None:
                try:
                    cand = best_fn(inp)
                    if _differs(cand):
                        return cand  # type: ignore[return-value]
                except Exception:
                    pass

        return a1  # absolute fallback: same grid as attempt_1

    def solve_rearc_challenge(self, challenge_path: str, output_path: str):
        """Generate a full RE-ARC submission from a challenge file.

        Each task gets two genuinely distinct attempt strategies:
          attempt_1: best primary stream (direct → engram → rearc[0] → color_map → nav_8aug)
          attempt_2: independent novel strategy via _novel_attempt2()
                     (rearc[1] → color_map → color_swap_nav → nav_4rot → nav_8aug)

        Attempts are deduplicated by output grid: attempt_2 falls back to a1
        only if every independent strategy agrees with it.
        """
        challenges = json.loads(Path(challenge_path).read_text())
        self.load_rearc_solvers()

        submission: Dict = {}
        t0 = time.time()

        for idx, (task_id, task) in enumerate(sorted(challenges.items())):
            test_cases = task.get('test', [])
            train = task.get('train', [])
            train_pairs = [(p['input'], p['output']) for p in train]
            test_outputs: List[Dict] = []

            # ── Phase 1: direct omega solver (fast path) ──────────────────────
            direct_fn = self._direct_solvers.get(task_id)
            all_pass = False
            if direct_fn:
                try:
                    all_pass = all(direct_fn(p['input']) == p['output'] for p in train)
                except Exception:
                    all_pass = False

            if direct_fn and all_pass:
                color_map_fn = self._color_map_fn(task)
                for tc in test_cases:
                    task_single = {'train': train, 'test': [tc]}
                    try:
                        a1: Grid = direct_fn(tc['input'])
                    except Exception:
                        a1 = tc['input']
                    if a1 is None:
                        a1 = tc['input']
                    a2 = self._novel_attempt2(tc['input'], task_single, task_id,
                                              a1, color_map_fn, [],
                                              skip_method='direct')
                    test_outputs.append({'attempt_1': a1, 'attempt_2': a2})
                submission[task_id] = test_outputs
                self._stats["matched"] += 1
                self._braid_emit_hermes(task_id, True, 1.0, ["skill-assignment"])
                print(f'  🎯 [{idx+1}/{len(challenges)}] {task_id} → omega/{task_id} (direct)')
                continue

            # ── Phase 2: per-task setup (shared across all test cases) ────────
            # Engram probe with first test case
            engram_hit: Optional[Grid] = None
            try:
                if test_cases:
                    engram_hit = EngramMemory().solve(train_pairs, test_cases[0]['input'])
            except Exception:
                engram_hit = None

            # Color-map function: cheap O(H×W×N), deterministic, computed once
            color_map_fn = self._color_map_fn(task)

            # Geometric transform: check if task is a pure rotation/reflection
            geo_hit = self._best_geo_transform(task)

            # Brute-force: find up to 2 independent RE-ARC solvers
            matches = self.match_all_tasks(task)

            # ── Phase 3: per test-case attempt assignment ──────────────────────
            for tc in test_cases:
                task_single = {'train': train, 'test': [tc]}
                inp = tc['input']

                # attempt_1: best available primary strategy
                a1: Optional[Grid] = None
                a1_method = 'fallback'

                if engram_hit is not None:
                    try:
                        a1 = EngramMemory().solve(train_pairs, inp)
                    except Exception:
                        a1 = None
                    if a1 is not None:
                        a1_method = 'engram'

                if a1 is None and matches:
                    try:
                        a1 = matches[0][1](inp)
                    except Exception:
                        a1 = None
                    if a1 is not None:
                        a1_method = 'rearc_0'

                if a1 is None and geo_hit is not None:
                    a1 = self._geo_transform_attempt_single(task_single, geo_hit)
                    if a1 is not None:
                        a1_method = 'geo'

                if a1 is None and color_map_fn is not None:
                    a1 = color_map_fn(inp)
                    if a1 is not None:
                        a1_method = 'color_map'

                if a1 is None:
                    try:
                        a1 = self._navigator_attempt(task_single, task_id)
                    except Exception:
                        a1 = None
                    if a1 is not None:
                        a1_method = 'nav_8aug'

                if a1 is None:
                    a1, a1_method = inp, 'identity'

                # attempt_2: novel independent strategy
                a2 = self._novel_attempt2(inp, task_single, task_id,
                                          a1, color_map_fn, matches,
                                          skip_method=a1_method,
                                          geo_hit=geo_hit)
                test_outputs.append({'attempt_1': a1, 'attempt_2': a2})

            submission[task_id] = test_outputs

            # Braid telemetry + console output
            if engram_hit is not None:
                self._stats["engram"] += 1
                self._braid_emit_simula(task_id, True, 0.95)
                print(f'  🧠 [{idx+1}/{len(challenges)}] {task_id} → engram memory')
            elif matches:
                self._stats["matched"] += 1
                self._braid_emit_hermes(task_id, True, 0.9, ["trigger-execution"])
                match_tag = f'{matches[0][0]}'
                if geo_hit:
                    match_tag += f' +geo({geo_hit[0]})'
                print(f'  ✅ [{idx+1}/{len(challenges)}] {task_id} → {match_tag}')
            elif geo_hit is not None:
                self._stats["matched"] += 1
                self._braid_emit_hermes(task_id, True, 0.85, ["skill-assignment"])
                print(f'  🔄 [{idx+1}/{len(challenges)}] {task_id} → geo({geo_hit[0]})')
            else:
                self._braid_emit_euphan(task_id, "spatial", 0.3, False)

            if (idx + 1) % 20 == 0:
                score = self.cohesion()
                coh_str = f"  cohesion={score.get('cohesion_score', 0):.3f}" if score else ""
                print(f'  ... {idx+1}/{len(challenges)} ({self._stats["matched"]} matched) '
                      f'[{time.time()-t0:.0f}s]{coh_str}')

        elapsed = time.time() - t0
        json.dump(submission, open(output_path, 'w'))

        coh = self.cohesion()
        print(f'\n{"="*50}')
        print(f'TranscendPlexity Omega — {self._stats["matched"]}/{len(challenges)} matched '
              f'({100*self._stats["matched"]/len(challenges):.1f}%)')
        if coh:
            print(f'Cohesion score: {coh.get("cohesion_score", 0):.3f}  '
                  f'(limb_balance={coh.get("limb_balance", 0):.3f}  '
                  f'skill_coverage={coh.get("skill_coverage", 0):.3f})')
            report_path = self.braid_report()
            print(f'Braid report:   {report_path}')
        print(f'Saved: {output_path}')
        print(f'Time: {elapsed:.1f}s')
        return submission

    def stats(self) -> Dict[str, int]:
        return dict(self._stats)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        e = TranscendPlexEngine()
        print(f"✅ TranscendPlexity Omega Engine v3.0  (+ Cognitive Cohesion Braid)")
        print(f"  Registry: {len(e.registry)} solvers loaded")
        print(f"  Braid: {'enabled' if _BRAID_AVAILABLE else 'unavailable (core/ not found)'}")
        print()
        print("Usage:")
        print("  python omega_engine.py <challenges.json>  — generate RE-ARC submission")
        print("  python omega_engine.py <task.json>        — solve a single task")
        return

    target = Path(sys.argv[1])
    engine = OmegaEngine(verbose=True)

    if target.is_file():
        task = json.loads(target.read_text())
        # Check if it's a RE-ARC challenge file (dict of task dicts)
        first_val = next(iter(task.values()))
        if isinstance(first_val, dict) and 'train' in first_val:
            out_path = str(target.parent / 'omega_submission.json')
            engine.solve_rearc_challenge(str(target), out_path)
        else:
            tid = engine._normalize_task_id(target.stem)
            result = engine.solve_task(task, tid)
            if result:
                print(f"\n✅ Solved {tid}")
                for row in result:
                    print("  ", row)
            else:
                print(f"\n❌ Could not solve {tid}")
    else:
        print(f"Error: {target} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
