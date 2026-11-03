import time
from pathlib import Path

from prism.core.watch import LiveRadarWatcher


def test_live_radar_watcher_init(tmp_path: Path):
    watcher = LiveRadarWatcher(target_dir=tmp_path, poll_interval=0.1)
    assert watcher.target_dir == tmp_path
    assert watcher.poll_interval == 0.1


def test_live_radar_watcher_detects_changes(tmp_path: Path):
    f = tmp_path / "service.py"
    f.write_text("def hello(): pass\n")

    watcher = LiveRadarWatcher(target_dir=tmp_path, poll_interval=0.02)
    call_count = [0]

    def on_change():
        call_count[0] += 1

    time.sleep(0.05)
    f.write_text("def hello(): return 42\n")

    # Run watcher for 1 iteration
    watcher.watch(on_change_callback=on_change, max_iterations=1)

    assert call_count[0] == 1


def test_live_radar_watcher_no_change_no_callback(tmp_path: Path):
    f = tmp_path / "service.py"
    f.write_text("def hello(): pass\n")

    watcher = LiveRadarWatcher(target_dir=tmp_path, poll_interval=0.02)
    call_count = [0]

    def on_change():
        call_count[0] += 1

    # Do not modify file, run for 1 iteration
    watcher.watch(on_change_callback=on_change, max_iterations=1)

    assert call_count[0] == 0
