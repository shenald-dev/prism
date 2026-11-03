"""
Live file watcher daemon for real-time PRISM radar during AI vibe-coding sessions.
Continuously audits working directory modifications and updates blast radius.
"""

import time
from pathlib import Path
from typing import Callable, Dict, Optional

from prism.core.git import discover_all_source_files


class LiveRadarWatcher:
    """Monitors repository source files and triggers callbacks upon changes."""

    def __init__(self, target_dir: Path, poll_interval: float = 0.5):
        self.target_dir = target_dir
        self.poll_interval = poll_interval
        self._last_mtimes: Dict[str, float] = self._get_mtimes()

    def _get_mtimes(self) -> Dict[str, float]:
        mtimes = {}
        files = discover_all_source_files(self.target_dir, include_tests=True)
        for f in files:
            try:
                mtimes[str(f)] = f.stat().st_mtime
            except OSError:
                pass
        return mtimes

    def watch(
        self,
        on_change_callback: Callable[[], None],
        max_iterations: Optional[int] = None,
    ):
        """Watch loop. Calls on_change_callback whenever a file is modified."""
        iterations = 0

        while True:
            time.sleep(self.poll_interval)
            current_mtimes = self._get_mtimes()

            changed = False
            if set(current_mtimes.keys()) != set(self._last_mtimes.keys()):
                changed = True
            else:
                for path_str, mtime in current_mtimes.items():
                    if mtime > self._last_mtimes.get(path_str, 0):
                        changed = True
                        break

            if changed:
                self._last_mtimes = current_mtimes
                on_change_callback()

            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
