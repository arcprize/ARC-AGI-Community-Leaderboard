import os, importlib.util
from pathlib import Path
from navigator import TranscendPlexNavigator

_DEFAULT_SOLVES_DIR = Path(__file__).resolve().parent / "solves"

class TranscendPlexEngine:
    def __init__(self, solves_dir: str | Path | None = None):
        solves_path = Path(solves_dir) if solves_dir else _DEFAULT_SOLVES_DIR
        self.solves_dir = str(solves_path)
        self.navigator = TranscendPlexNavigator()
        self.registry = {d: str(solves_path / d / 'solver.py')
                        for d in os.listdir(solves_path) if (solves_path / d).is_dir()}

    def solve(self, task_id, grid):
        if task_id in self.registry:
            print(f"🎯 System 1: Verified Match for {task_id}")
            return self._exec(task_id, grid)
        print(f"🌀 System 2: No Match. Engaging 8-Stream Vortex for {task_id}")
        return self.navigator.solve_vortex(grid, task_id)

    def _exec(self, task_id, grid):
        spec = importlib.util.spec_from_file_location("s", self.registry[task_id])
        s = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(s)
        return s.solve(grid)

if __name__ == "__main__":
    e = TranscendPlexEngine()
    print(f"✅ Omega Engine Online: {len(e.registry)} Solvers Loaded.")
