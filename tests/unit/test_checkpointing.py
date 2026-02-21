"""Unit tests for the checkpointing logic in AnalysisService."""

import json
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import pytest

from strava_analyzer.constants import CSVConstants
from strava_analyzer.services.analysis_service import (
    DEFAULT_CHECKPOINT_INTERVAL,
    AnalysisService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(tmp_path: Path) -> MagicMock:
    """Build a minimal mock ``Settings`` with real ``processed_data_dir``."""
    s = MagicMock()
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    s.processed_data_dir = processed
    s.ftp = 250
    s.fthr = 170
    s.lt1_power = 0
    s.lt2_power = 0
    s.lt1_hr = 0
    s.lt2_hr = 0
    s.rider_weight_kg = 75.0
    s.max_hr = 0
    s.cp = 0
    s.w_prime = 0
    return s


def _write_checkpoint(
    processed_dir: Path,
    raw_rows: list[dict],
    moving_rows: list[dict],
    processed_ids: list[int],
) -> None:
    """Write checkpoint files directly (simulates a previous partial run)."""
    pd.DataFrame(raw_rows).to_csv(
        processed_dir / ".checkpoint_raw.csv",
        index=False,
        sep=CSVConstants.DEFAULT_SEPARATOR,
    )
    pd.DataFrame(moving_rows).to_csv(
        processed_dir / ".checkpoint_moving.csv",
        index=False,
        sep=CSVConstants.DEFAULT_SEPARATOR,
    )
    manifest = {"processed_ids": processed_ids, "count": len(processed_ids)}
    with open(processed_dir / ".checkpoint_manifest.json", "w") as f:
        json.dump(manifest, f)


# ---------------------------------------------------------------------------
# Test: _has_checkpoint
# ---------------------------------------------------------------------------


class TestHasCheckpoint:
    def test_no_files(self, tmp_path):
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        assert svc._has_checkpoint() is False

    def test_only_manifest(self, tmp_path):
        (tmp_path / ".checkpoint_manifest.json").write_text("{}")
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        assert svc._has_checkpoint() is False

    def test_all_files_present(self, tmp_path):
        (tmp_path / ".checkpoint_manifest.json").write_text("{}")
        (tmp_path / ".checkpoint_raw.csv").write_text("id\n1")
        (tmp_path / ".checkpoint_moving.csv").write_text("id\n1")
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        assert svc._has_checkpoint() is True


# ---------------------------------------------------------------------------
# Test: _save_checkpoint / _load_checkpoint round-trip
# ---------------------------------------------------------------------------


class TestCheckpointRoundTrip:
    def test_save_then_load(self, tmp_path):
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        svc.logger = MagicMock()

        raw = [{"id": 1, "metric": 10.0}, {"id": 2, "metric": 20.0}]
        mov = [{"id": 1, "metric": 11.0}, {"id": 2, "metric": 21.0}]
        ids = {1, 2}

        svc._save_checkpoint(raw, mov, ids)

        # All three checkpoint files should exist
        assert svc._has_checkpoint()

        loaded_raw, loaded_mov, loaded_ids = svc._load_checkpoint()
        assert loaded_ids == ids
        assert len(loaded_raw) == 2
        assert len(loaded_mov) == 2
        # Values should survive the round-trip
        assert loaded_raw[0]["id"] == 1
        assert loaded_raw[1]["metric"] == 20.0

    def test_load_corrupt_manifest_returns_empty(self, tmp_path):
        """Corrupt JSON manifest → fallback to empty."""
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        svc.logger = MagicMock()

        (tmp_path / ".checkpoint_manifest.json").write_text("NOT JSON")
        (tmp_path / ".checkpoint_raw.csv").write_text("id\n1")
        (tmp_path / ".checkpoint_moving.csv").write_text("id\n1")

        raw, mov, ids = svc._load_checkpoint()
        assert raw == []
        assert mov == []
        assert ids == set()
        # Corrupt files should have been cleaned up
        assert not svc._has_checkpoint()


# ---------------------------------------------------------------------------
# Test: _cleanup_checkpoint
# ---------------------------------------------------------------------------


class TestCleanupCheckpoint:
    def test_removes_all_files(self, tmp_path):
        (tmp_path / ".checkpoint_manifest.json").write_text("{}")
        (tmp_path / ".checkpoint_raw.csv").write_text("")
        (tmp_path / ".checkpoint_moving.csv").write_text("")

        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path

        svc._cleanup_checkpoint()

        assert not (tmp_path / ".checkpoint_manifest.json").exists()
        assert not (tmp_path / ".checkpoint_raw.csv").exists()
        assert not (tmp_path / ".checkpoint_moving.csv").exists()

    def test_cleanup_idempotent(self, tmp_path):
        """Cleaning up when no checkpoint files exist should not raise."""
        svc = AnalysisService.__new__(AnalysisService)
        svc._checkpoint_dir = tmp_path
        svc._cleanup_checkpoint()  # should not raise


# ---------------------------------------------------------------------------
# Test: _process_activities respects checkpoints
# ---------------------------------------------------------------------------


class TestProcessActivitiesCheckpoint:
    """Verify that _process_activities() uses checkpointing correctly."""

    def _make_service(self, tmp_path, checkpoint_interval=2):
        """Create a minimal AnalysisService with mocked sub-services."""
        settings = _make_settings(tmp_path)
        svc = AnalysisService.__new__(AnalysisService)
        svc.settings = settings
        svc.logger = MagicMock()
        svc.checkpoint_interval = checkpoint_interval
        svc._checkpoint_dir = settings.processed_data_dir
        svc.activity_service = MagicMock()
        return svc

    def test_checkpoint_skips_already_processed(self, tmp_path):
        """Activities present in a checkpoint should be skipped."""
        svc = self._make_service(tmp_path, checkpoint_interval=0)

        # Pre-write a checkpoint with activity 100 already done
        _write_checkpoint(
            svc._checkpoint_dir,
            raw_rows=[{"id": 100, "val": 1}],
            moving_rows=[{"id": 100, "val": 2}],
            processed_ids=[100],
        )

        activities_df = pd.DataFrame({"id": [100, 200]})
        # Only activity 200 should be processed
        result = MagicMock()
        result.raw_metrics = {"val": 10}
        result.moving_metrics = {"val": 20}
        svc.activity_service.activity_has_stream.return_value = True
        svc.activity_service.process_activity.return_value = (result, None)

        raw_df, moving_df = svc._process_activities(activities_df, None)

        # Should contain both: checkpoint (100) + newly processed (200)
        assert set(raw_df["id"].tolist()) == {100, 200}
        # process_activity should only have been called for activity 200
        assert svc.activity_service.process_activity.call_count == 1

    def test_periodic_checkpoint_written(self, tmp_path):
        """A checkpoint file should be written every N activities."""
        svc = self._make_service(tmp_path, checkpoint_interval=2)

        activities_df = pd.DataFrame({"id": [1, 2, 3]})
        result = MagicMock()
        result.raw_metrics = {"val": 1}
        result.moving_metrics = {"val": 2}
        svc.activity_service.activity_has_stream.return_value = True
        svc.activity_service.process_activity.return_value = (result, None)

        svc._process_activities(activities_df, None)

        # After processing 3 activities with interval=2, we should see checkpoint
        # files on disk (written at 2 and again at final flush for the 3rd).
        assert svc._has_checkpoint()
        with open(svc._checkpoint_manifest_path) as f:
            manifest = json.load(f)
        assert manifest["count"] == 3

    def test_no_checkpoint_when_interval_zero(self, tmp_path):
        """When checkpoint_interval=0, no periodic checkpoint should be saved,
        but the final safety flush should still occur."""
        svc = self._make_service(tmp_path, checkpoint_interval=0)

        activities_df = pd.DataFrame({"id": [1, 2]})
        result = MagicMock()
        result.raw_metrics = {"val": 1}
        result.moving_metrics = {"val": 2}
        svc.activity_service.activity_has_stream.return_value = True
        svc.activity_service.process_activity.return_value = (result, None)

        svc._process_activities(activities_df, None)

        # Final safety flush should have been written
        assert svc._has_checkpoint()


# ---------------------------------------------------------------------------
# Test: save_results cleans up checkpoint
# ---------------------------------------------------------------------------


class TestSaveResultsCheckpointCleanup:
    def test_checkpoint_cleaned_after_save(self, tmp_path):
        """After save_results() completes, checkpoint files should be gone."""
        settings = _make_settings(tmp_path)
        svc = AnalysisService.__new__(AnalysisService)
        svc.settings = settings
        svc.logger = MagicMock()
        svc._checkpoint_dir = settings.processed_data_dir

        # Create a dummy checkpoint
        _write_checkpoint(
            svc._checkpoint_dir,
            raw_rows=[{"id": 1}],
            moving_rows=[{"id": 1}],
            processed_ids=[1],
        )
        assert svc._has_checkpoint()

        # Build a minimal DualAnalysisResult mock
        from strava_analyzer.services.analysis_service import DualAnalysisResult

        raw_df = pd.DataFrame({"id": [1], "start_date_local": ["2024-01-15"]})
        moving_df = pd.DataFrame({"id": [1], "start_date_local": ["2024-01-15"]})
        summary = MagicMock()
        summary.model_dump.return_value = {"total_activities": 1}

        result = DualAnalysisResult(raw_df=raw_df, moving_df=moving_df, summary=summary)

        # Patch _prepare_df_for_export to pass-through
        svc._prepare_df_for_export = lambda df: df

        svc.save_results(result)

        assert not svc._has_checkpoint()


# ---------------------------------------------------------------------------
# Test: default checkpoint_interval
# ---------------------------------------------------------------------------


class TestDefaultCheckpointInterval:
    def test_default_value(self, tmp_path):
        settings = _make_settings(tmp_path)
        # We can't call __init__ because it would try to instantiate real
        # sub-services, so just test the constant.
        assert DEFAULT_CHECKPOINT_INTERVAL == 50
