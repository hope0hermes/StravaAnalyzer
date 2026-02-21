"""Unit tests for the --recompute-from feature in AnalysisService."""

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from strava_analyzer.services.analysis_service import AnalysisService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(tmp_path: Path) -> AnalysisService:
    """Build a minimal AnalysisService with mocked sub-services."""
    svc = AnalysisService.__new__(AnalysisService)
    svc.settings = MagicMock()
    svc.settings.processed_data_dir = tmp_path
    svc.logger = MagicMock()
    return svc


def _make_enriched_df() -> pd.DataFrame:
    """Create a small enriched DataFrame spanning Jan–Jun 2024."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "start_date_local": [
                "2024-01-15T08:00:00Z",
                "2024-03-01T09:00:00Z",
                "2024-05-20T10:00:00Z",
                "2024-06-10T11:00:00Z",
            ],
            "ftp": [250, 250, 260, 260],
        }
    )


# ---------------------------------------------------------------------------
# _prune_activities_from_date
# ---------------------------------------------------------------------------


class TestPruneActivitiesFromDate:
    """Tests for _prune_activities_from_date()."""

    def test_prune_removes_activities_on_or_after_date(self, tmp_path):
        svc = _make_service(tmp_path)
        raw = _make_enriched_df()
        mov = _make_enriched_df()

        pruned_raw, pruned_mov = svc._prune_activities_from_date(
            raw, mov, "2024-05-01"
        )

        # Activities 1 and 2 (Jan and Mar) should remain
        assert list(pruned_raw["id"]) == [1, 2]
        assert list(pruned_mov["id"]) == [1, 2]

    def test_prune_keeps_all_when_date_in_future(self, tmp_path):
        svc = _make_service(tmp_path)
        raw = _make_enriched_df()

        pruned_raw, _ = svc._prune_activities_from_date(raw, None, "2025-01-01")
        assert len(pruned_raw) == 4

    def test_prune_removes_all_when_date_before_first(self, tmp_path):
        svc = _make_service(tmp_path)
        raw = _make_enriched_df()

        pruned_raw, _ = svc._prune_activities_from_date(raw, None, "2024-01-01")
        assert len(pruned_raw) == 0

    def test_prune_handles_none_moving_df(self, tmp_path):
        svc = _make_service(tmp_path)
        raw = _make_enriched_df()

        pruned_raw, pruned_mov = svc._prune_activities_from_date(
            raw, None, "2024-05-01"
        )
        assert pruned_mov is None
        assert len(pruned_raw) == 2

    def test_prune_handles_empty_moving_df(self, tmp_path):
        svc = _make_service(tmp_path)
        raw = _make_enriched_df()
        empty_mov = pd.DataFrame()

        pruned_raw, pruned_mov = svc._prune_activities_from_date(
            raw, empty_mov, "2024-05-01"
        )
        assert pruned_mov is not None
        assert pruned_mov.empty

    def test_prune_uses_start_date_fallback(self, tmp_path):
        """When ``start_date_local`` doesn't exist, fall back to ``start_date``."""
        svc = _make_service(tmp_path)
        raw = pd.DataFrame(
            {
                "id": [1, 2],
                "start_date": [
                    "2024-01-15T08:00:00Z",
                    "2024-06-10T11:00:00Z",
                ],
            }
        )

        pruned_raw, _ = svc._prune_activities_from_date(raw, None, "2024-03-01")
        assert list(pruned_raw["id"]) == [1]

    def test_prune_exact_boundary(self, tmp_path):
        """Activity exactly on the boundary date should be removed."""
        svc = _make_service(tmp_path)
        raw = pd.DataFrame(
            {
                "id": [1, 2],
                "start_date_local": [
                    "2024-05-01T00:00:00Z",
                    "2024-04-30T23:59:59Z",
                ],
            }
        )

        pruned_raw, _ = svc._prune_activities_from_date(raw, None, "2024-05-01")
        assert list(pruned_raw["id"]) == [2]
