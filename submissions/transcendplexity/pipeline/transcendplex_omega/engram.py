#!/usr/bin/env python3
"""
Engram — Associative Pattern Memory for ARC Grids
Inspired by DeepSeek's Engram paper (2025).

Core idea: instead of spending solver streams "figuring out" the rule,
pre-load learned associations from training pairs into three lookup tables,
then query them with conservative gating before the vortex streams run.

Tables (all exact-key Python dicts, no hash collisions):
  unigram   : cell_value → Counter of output colors
  bigram    : (center, neighbor, direction) → Counter of output colors
  context   : tuple(3×3 patch values) → Counter of output colors

Design choices from rubber-duck critique:
  - Exact tuple keys (not fixed-size hash buckets) → zero collisions
  - Leave-one-out validation → no training-time leakage
  - Same-shape early exit → never fires on resize/crop/tile tasks
  - Coverage gate → abstain if >30% of test cells have unseen 3×3 context
  - Evidence-based gating (support count + top1/top2 margin) not magic thresholds
"""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

Grid = List[List[int]]

# sentinel for out-of-bounds cells in padded patches
_OOB = -1


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pad(g: Grid, r: int, c: int, half: int = 1) -> Tuple:
    """Return a flat tuple of the (2*half+1)² neighbourhood centred on (r,c).
    Out-of-bounds positions are filled with _OOB sentinel (not toroidal wrap)."""
    H, W = len(g), len(g[0])
    patch = []
    for dr in range(-half, half + 1):
        for dc in range(-half, half + 1):
            nr, nc = r + dr, c + dc
            patch.append(g[nr][nc] if 0 <= nr < H and 0 <= nc < W else _OOB)
    return tuple(patch)


_DIRS = ((-1, 0, "N"), (1, 0, "S"), (0, -1, "W"), (0, 1, "E"))


def _confidence(cnt: Counter, min_support: int = 2) -> Tuple[Optional[int], float]:
    """Return (best_color, confidence) or (None, 0) if evidence is too weak.

    Confidence = 1 - (second_best / best).  High margin → high confidence.
    Requires at least `min_support` observations for the top prediction.
    """
    if not cnt:
        return None, 0.0
    ranked = cnt.most_common(2)
    best_color, best_count = ranked[0]
    if best_count < min_support:
        return None, 0.0
    total = sum(cnt.values())
    second = ranked[1][1] if len(ranked) > 1 else 0
    margin = 1.0 - second / best_count  # 1.0 = unanimous, 0.0 = tied
    conf = (best_count / total) * margin
    return best_color, conf


# ---------------------------------------------------------------------------
# EngramMemory
# ---------------------------------------------------------------------------

class EngramMemory:
    """
    Associative memory built from ARC training pairs.

    Usage:
        mem = EngramMemory()
        result = mem.solve(pairs, test_input)   # → Grid or None
    """

    # Minimum per-pair cell accuracy required during LOO validation.
    # 1.0 = exact reconstruction required (safe for ARC: any wrong cell = task failed).
    # Coverage-failed pairs (None from _apply) are skipped, not penalised.
    LOO_ACCURACY = 1.0
    # Minimum number of assessable pairs needed to trust LOO.
    LOO_MIN_ASSESSABLE = 2
    # Maximum fraction of test cells allowed to have an unseen 3×3 context.
    COVERAGE_THRESHOLD = 0.30

    def __init__(self) -> None:
        self.unigram:  Dict[int, Counter]             = {}
        self.bigram:   Dict[Tuple, Counter]            = {}
        self.context:  Dict[Tuple, Counter]            = {}

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def build(self, pairs: List[Tuple[Grid, Grid]]) -> None:
        """Populate all three tables from the given training pairs."""
        self.unigram.clear()
        self.bigram.clear()
        self.context.clear()

        for inp, out in pairs:
            H, W = len(inp), len(inp[0])
            for r in range(H):
                for c in range(W):
                    val    = inp[r][c]
                    target = out[r][c]

                    # unigram
                    if val not in self.unigram:
                        self.unigram[val] = Counter()
                    self.unigram[val][target] += 1

                    # bigrams (direction-aware to preserve order)
                    for dr, dc, tag in _DIRS:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < H and 0 <= nc < W:
                            key = (val, inp[nr][nc], tag)
                            if key not in self.bigram:
                                self.bigram[key] = Counter()
                            self.bigram[key][target] += 1

                    # 3×3 context patch
                    patch = _pad(inp, r, c)
                    if patch not in self.context:
                        self.context[patch] = Counter()
                    self.context[patch][target] += 1

    # ------------------------------------------------------------------
    # query one cell
    # ------------------------------------------------------------------

    def query(self, inp: Grid, r: int, c: int) -> Tuple[Optional[int], float]:
        """Return (predicted_color, confidence) for cell (r, c).

        Waterfall priority: context (3×3) > bigram > unigram.
        Returns (None, 0.0) when evidence is insufficient.
        min_support scales down to 1 so LOO with a single training pair still
        fires — the confidence threshold is the real quality gate.
        """
        val = inp[r][c]
        H, W = len(inp), len(inp[0])

        # --- 3×3 context (highest specificity) ---
        patch = _pad(inp, r, c)
        color, conf = _confidence(self.context.get(patch, Counter()), min_support=1)
        if color is not None and conf >= 0.85:
            return color, conf

        # --- bigrams (4 directions, vote) ---
        votes: Counter = Counter()
        for dr, dc, tag in _DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W:
                key = (val, inp[nr][nc], tag)
                color_b, conf_b = _confidence(self.bigram.get(key, Counter()), min_support=1)
                if color_b is not None and conf_b >= 0.75:
                    votes[color_b] += conf_b
        if votes:
            best = votes.most_common(1)[0][0]
            total = sum(votes.values())
            agg_conf = votes[best] / total
            if agg_conf >= 0.70:
                return best, agg_conf

        # --- unigram (lowest specificity) ---
        color_u, conf_u = _confidence(self.unigram.get(val, Counter()), min_support=1)
        if color_u is not None and conf_u >= 0.80:
            return color_u, conf_u

        return None, 0.0

    # ------------------------------------------------------------------
    # apply to a full grid
    # ------------------------------------------------------------------

    def _apply(self, inp: Grid) -> Optional[Grid]:
        """Apply Engram memory to every cell of `inp`.

        Returns predicted output grid, or None if coverage is too low
        (i.e., too many cells have no confident prediction).
        """
        H, W = len(inp), len(inp[0])
        out   = [[0] * W for _ in range(H)]
        unseen = 0

        for r in range(H):
            for c in range(W):
                color, conf = self.query(inp, r, c)
                if color is None:
                    # fall back to identity for this cell
                    out[r][c] = inp[r][c]
                    unseen += 1
                else:
                    out[r][c] = color

        coverage_miss = unseen / (H * W)
        if coverage_miss > self.COVERAGE_THRESHOLD:
            return None  # too many unseen contexts → abstain
        return out

    # ------------------------------------------------------------------
    # leave-one-out validation
    # ------------------------------------------------------------------

    def _loo_valid(self, pairs: List[Tuple[Grid, Grid]]) -> bool:
        """Return True if Engram generalises well across leave-one-out folds.

        Rules:
          - Pairs whose held-out input has too-low coverage (_apply → None)
            are skipped (coverage gate will also block the test if needed).
          - At least LOO_MIN_ASSESSABLE pairs must be assessable.
          - Every assessable held-out pair must achieve >= LOO_ACCURACY
            cell-level accuracy.
        """
        if len(pairs) < 2:
            return False

        assessable = 0
        for i in range(len(pairs)):
            held_inp, held_out = pairs[i]
            others = [p for j, p in enumerate(pairs) if j != i]
            mem = EngramMemory()
            mem.build(others)
            pred = mem._apply(held_inp)
            if pred is None:
                continue  # coverage failure → skip this fold
            H, W = len(held_out), len(held_out[0])
            correct = sum(
                pred[r][c] == held_out[r][c]
                for r in range(H) for c in range(W)
            )
            accuracy = correct / (H * W)
            if accuracy < self.LOO_ACCURACY:
                return False  # this fold is too inaccurate
            assessable += 1

        return assessable >= self.LOO_MIN_ASSESSABLE

    # ------------------------------------------------------------------
    # public solve entry point
    # ------------------------------------------------------------------

    def solve(
        self,
        pairs:      List[Tuple[Grid, Grid]],
        test_input: Grid,
    ) -> Optional[Grid]:
        """Attempt to solve using associative memory.

        Steps:
          1. Same-shape guard — skip if any pair changes grid dimensions
          2. Leave-one-out validation — ensures generalisation, not memorisation
          3. Build full tables from all pairs
          4. Apply to test input with coverage gate
        """
        if not pairs:
            return None

        # 1. same-shape guard
        for inp, out in pairs:
            if len(inp) != len(out) or (inp and out and len(inp[0]) != len(out[0])):
                return None

        # 2. leave-one-out validation
        if not self._loo_valid(pairs):
            return None

        # 3. build on all pairs
        self.build(pairs)

        # 4. apply to test
        return self._apply(test_input)
