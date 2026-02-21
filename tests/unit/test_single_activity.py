"""Tests for single-activity processing (Phase 5)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from strava_analyzer.constants import CSVConstants
from strava_analyzer.pipeline import Pipeline


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings with real temp paths."""
    settings = MagicMock()
    settings.processed_data_dir = tmp_path
    settings.data_dir = tmp_path
    settings.activities_file = tmp_path / "activities.csv"
    settings.streams_dir = tmp_path / "Streams"
    settings.ftp = 285
    settings.fthr = 170
    settings.rider_weight_kg = 77.0
    settings.max_hr = 190
    settings.cp = 0
    settings.w_prime = 0
    settings.lt1_power = None
    settings.lt2_power = None
    settings.lt1_hr = None
    settings.lt2_hr = None
    return settings


class TestProcessSingleActivity:
    """Tests for Pipeline.process_single_activity()."""

    @patch.object(Pipeline, "__init__", lambda self, *a, **kw: None)
    def test_removes_activity_from_existing_data_before_reprocess(self, tmp_path):
        """Prunes the target activity from existing CSVs before re-running."""
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.settings = MagicMock()
        pipeline.settings.processed_data_dir = tmp_path
        pipeline.logger = MagicMock()
        pipeline.analysis_service = MagicMock()

        # Create fake existing files
        existing = pd.DataFrame({
            "id": [111, 222, 333],
            "start_date_local": ["2024-01-01", "2024-02-01", "2024-03-01"],
        })
        raw_file = tmp_path / "activities_raw.csv"
        moving_file = tmp_path / "activities_moving.csv"
        existing.to_csv(raw_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR)
        existing.to_csv(moving_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR)

        # Mock run_analysis result
        mock_result = MagicMock()
        pipeline.analysis_service.run_analysis.return_value = mock_result

        pipeline.process_single_activity(222)

        # The activity 222 should have been removed from both files
        raw_after = pd.read_csv(raw_file, sep=CSVConstants.DEFAULT_SEPARATOR)
        assert 222 not in raw_after["id"].values
        assert 111 in raw_after["id"].values
        assert 333 in raw_after["id"].values

        moving_after = pd.read_csv(moving_file, sep=CSVConstants.DEFAULT_SEPARATOR)
        assert 222 not in moving_after["id"].values

        # run_analysis and save_results should be called
        pipeline.analysis_service.run_analysis.assert_called_once()
        pipeline.analysis_service.save_results.assert_called_once_with(mock_result)

    @patch.object(Pipeline, "__init__", lambda self, *a, **kw: None)
    def test_works_when_no_existing_files(self, tmp_path):
        """Handles the case where no enriched files exist yet."""
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.settings = MagicMock()
        pipeline.settings.processed_data_dir = tmp_path
        pipeline.logger = MagicMock()
        pipeline.analysis_service = MagicMock()

        mock_result = MagicMock()
        pipeline.analysis_service.run_analysis.return_value = mock_result

        # Should not raise
        pipeline.process_single_activity(99999)

        pipeline.analysis_service.run_analysis.assert_called_once()
        pipeline.analysis_service.save_results.assert_called_once_with(mock_result)

    @patch.object(Pipeline, "__init__", lambda self, *a, **kw: None)
    def test_activity_not_in_existing_data(self, tmp_path):
        """Activity ID not in existing data: no rows removed, still runs."""
        pipeline = Pipeline.__new__(Pipeline)
        pipeline.settings = MagicMock()
        pipeline.settings.processed_data_dir = tmp_path
        pipeline.logger = MagicMock()
        pipeline.analysis_service = MagicMock()

        existing = pd.DataFrame({"id": [111, 222], "name": ["A", "B"]})
        raw_file = tmp_path / "activities_raw.csv"
        existing.to_csv(raw_file, index=False, sep=CSVConstants.DEFAULT_SEPARATOR)

        mock_result = MagicMock()
        pipeline.analysis_service.run_analysis.return_value = mock_result

        pipeline.process_single_activity(99999)

        # All original rows should remain
        raw_after = pd.read_csv(raw_file, sep=CSVConstants.DEFAULT_SEPARATOR)
        assert len(raw_after) == 2

        pipeline.analysis_service.run_analysis.assert_called_once()
