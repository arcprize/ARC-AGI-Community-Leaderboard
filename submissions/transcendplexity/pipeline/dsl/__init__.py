"""
F.A.R.T.S. Grid DSL
===================
A typed, compositional language for ARC-AGI grid transformations.

Layers
------
  primitives   — pure functions on Grid / ObjSet / Color
  perception   — object detection, separators, symmetry
  synthesizer  — program-synthesis engine (enumerative + pattern heuristics)
  meta_solver  — HybridARCSolver-compatible entry point

Quick start
-----------
    from dsl import MetaSolver
    solver = MetaSolver()
    preds  = solver.solve(task)          # task = {"train": [...], "test": [...]}
"""

from dsl.primitives import (
    Grid, Object, BBox,
    rotate, flip_h, flip_v,
    crop, hstack, vstack,
    paint, clear_grid, fill_grid,
    recolor, apply_color_map,
    grid_or, grid_and, grid_xor,
    background, color_histogram, colors_in,
    tile_grid,
)
from dsl.perception import (
    find_objects,
    bounding_box,
    object_color,
    normalize_shape,
    find_separators,
    split_by_separators,
    symmetry_flags,
)
from dsl.synthesizer import Synthesizer
from dsl.meta_solver import MetaSolver

__all__ = [
    "Grid", "Object", "BBox",
    "rotate", "flip_h", "flip_v",
    "crop", "hstack", "vstack",
    "paint", "clear_grid", "fill_grid",
    "recolor", "apply_color_map",
    "grid_or", "grid_and", "grid_xor",
    "background", "color_histogram", "colors_in",
    "tile_grid",
    "find_objects", "bounding_box", "object_color",
    "normalize_shape", "find_separators", "split_by_separators",
    "symmetry_flags",
    "Synthesizer", "MetaSolver",
]
