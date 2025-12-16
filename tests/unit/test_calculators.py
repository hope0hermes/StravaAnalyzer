"""Unit tests for base calculator and time-weighted averaging."""

import numpy as np
import pandas as pd
import pytest

from strava_analyzer.metrics.base import BaseMetricCalculator
from strava_analyzer.settings import Settings


class MockCalculator(BaseMetricCalculator):
    """Mock calculator for testing base class functionality."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """Mock implementation."""
        return {}


class TestTimeWeightedMean:
    """Test time-weighted mean calculation (critical feature)."""

    def test_uniform_time_intervals(self, settings_with_ftp: Settings):
        """Test time-weighted mean with uniform 1-second intervals."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4],
                "watts": [100, 200, 300, 400, 500],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # With uniform intervals, should be simple mean
        expected = 300.0
        assert result == pytest.approx(expected, rel=1e-3)

    def test_non_uniform_time_intervals(self, settings_with_ftp: Settings):
        """Test time-weighted mean with non-uniform intervals."""
        calculator = MockCalculator(settings_with_ftp)

        # 200W for 1 second, 400W for 9 seconds
        stream = pd.DataFrame(
            {
                "time": [0, 1, 10],
                "watts": [200, 200, 400],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # time_deltas with diff(): [NaN, 1, 9] -> first gets second's value -> [1, 1, 9]
        # Weighted: (200*1 + 200*1 + 400*9) / (1+1+9) = (200+200+3600)/11 = 363.64
        expected = (200 * 1 + 200 * 1 + 400 * 9) / (1 + 1 + 9)
        assert result == pytest.approx(expected, rel=1e-2)

    def test_time_weighted_with_long_stop(self, settings_with_ftp: Settings):
        """Test that long stopped periods are weighted correctly."""
        calculator = MockCalculator(settings_with_ftp)

        # 300W for 10 seconds, 0W for 50 seconds (stop), 300W for 10 seconds
        stream = pd.DataFrame(
            {
                "time": [0, 10, 60, 70],
                "watts": [300, 300, 0, 300],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # time_deltas: diff gives [NaN, 10, 50, 10],
        # first gets second -> [10, 10, 50, 10]
        # weighted: (300*10 + 300*10 + 0*50 + 300*10) / (10+10+50+10) = 9000/80 = 112.5
        expected = (300 * 10 + 300 * 10 + 0 * 50 + 300 * 10) / (10 + 10 + 50 + 10)
        assert result == pytest.approx(expected, rel=1e-2)

    def test_time_weighted_with_gaps(self, settings_with_ftp: Settings):
        """Test time-weighted mean handles gaps in time data.

        NOTE: In the new architecture, data is pre-split into raw/moving DataFrames
        upstream. Moving data has contiguous time (via np.arange), so gap handling
        is less critical. This test validates basic gap behavior in raw data.
        """
        calculator = MockCalculator(settings_with_ftp)

        # Simulate data with gaps
        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 52, 53, 54],  # 50-second gap
                "watts": [200, 250, 300, 200, 250, 300],
            }
        )

        # Time-weighted mean should still work with gaps
        result = calculator._time_weighted_mean(stream["watts"], stream)

        # Result should be finite and reasonable
        assert result > 0
        assert result < 500  # Sanity check

    def test_empty_series(self, settings_with_ftp: Settings):
        """Test time-weighted mean of empty series."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [], "watts": []})
        result = calculator._time_weighted_mean(stream["watts"], stream)

        assert result == 0.0

    def test_single_value(self, settings_with_ftp: Settings):
        """Test time-weighted mean with single value."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0], "watts": [250]})
        result = calculator._time_weighted_mean(stream["watts"], stream)

        assert result == pytest.approx(250.0, rel=1e-3)


class TestTimeDeltas:
    """Test time delta calculations."""

    def test_time_deltas_uniform(self, settings_with_ftp: Settings):
        """Test time deltas with uniform intervals."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0, 1, 2, 3, 4]})
        deltas = calculator._calculate_time_deltas(stream)

        # All deltas should be 1.0 second
        assert len(deltas) == 5
        assert all(deltas == 1.0)

    def test_time_deltas_non_uniform(self, settings_with_ftp: Settings):
        """Test time deltas with non-uniform intervals."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0, 1, 5, 10, 20]})
        deltas = calculator._calculate_time_deltas(stream)

        # diff() gives [NaN, 1, 4, 5, 10], first gets second's value
        # Result: [1, 1, 4, 5, 10]
        assert deltas.iloc[0] == 1.0  # First gets second's delta
        assert deltas.iloc[1] == 1.0  # This is the actual second element after diff
        assert deltas.iloc[2] == 4.0
        assert deltas.iloc[3] == 5.0
        assert deltas.iloc[4] == 10.0

    def test_time_deltas_with_large_gap(self, settings_with_ftp: Settings):
        """Test time deltas with large gaps in data.

        NOTE: In the new architecture, data is pre-split into raw/moving DataFrames
        upstream. Moving data has contiguous time (via np.arange), so gap clipping
        is no longer needed. This test validates basic gap handling in raw data.
        """
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0, 1, 100]})  # 99-second gap

        deltas = calculator._calculate_time_deltas(stream)

        # Gap is preserved without clipping (as expected for raw data)
        assert deltas.iloc[2] == 99.0

    def test_time_deltas_negative_handling(self, settings_with_ftp: Settings):
        """Test that negative time deltas are handled (defensive test)."""
        calculator = MockCalculator(settings_with_ftp)

        # Create artificially bad data
        stream = pd.DataFrame({"time": [5, 4, 3, 2, 1]})  # Decreasing time
        deltas = calculator._calculate_time_deltas(stream)

        # Negative deltas should be clipped to 1.0
        assert all(deltas >= 1.0)

    def test_time_deltas_missing_time_column(self, settings_with_ftp: Settings):
        """Test fallback when time column is missing."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"watts": [100, 200, 300]})
        deltas = calculator._calculate_time_deltas(stream)

        # Should fallback to 1.0 for all points
        assert len(deltas) == 3
        assert all(deltas == 1.0)


class TestTotalDuration:
    """Test total duration calculation."""

    def test_total_duration_uniform(self, settings_with_ftp: Settings):
        """Test total duration with uniform intervals."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0, 1, 2, 3, 4]})  # 5 points, 1-second intervals
        duration = calculator._get_total_duration(stream)

        # Total duration = sum of deltas = 1+1+1+1+1 = 5 seconds
        assert duration == 5.0

    def test_total_duration_non_uniform(self, settings_with_ftp: Settings):
        """Test total duration with non-uniform intervals."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [0, 10, 30, 60]})
        duration = calculator._get_total_duration(stream)

        # diff gives [NaN, 10, 20, 30], first gets second -> [10, 10, 20, 30]
        # Total: 10+10+20+30 = 70
        expected = 10 + 10 + 20 + 30
        assert duration == pytest.approx(expected, rel=1e-3)

    def test_total_duration_with_gaps(
        self, stream_with_gaps: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test that gaps are included in total duration."""
        calculator = MockCalculator(settings_with_ftp)

        duration = calculator._get_total_duration(stream_with_gaps)

        # Should include all time including gaps
        assert duration > 0

    def test_total_duration_empty(self, settings_with_ftp: Settings):
        """Test total duration of empty stream."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": []})
        duration = calculator._get_total_duration(stream)

        assert duration == 0.0


# NOTE: TestFilterMoving and TestGetPrefix classes have been removed.
# The new architecture pre-splits data into raw/moving DataFrames upstream
# using StreamSplitter, so these methods are no longer needed in the calculators.


class TestTimeWeightedEdgeCases:
    """Test edge cases in time-weighted calculations."""

    def test_all_zeros_with_time_weighting(self, settings_with_ftp: Settings):
        """Test time-weighted mean of all zeros."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3],
                "watts": [0, 0, 0, 0],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)
        assert result == 0.0

    def test_nan_handling(self, settings_with_ftp: Settings):
        """Test that NaN values are handled in time-weighted mean."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3],
                "watts": [200, np.nan, 300, 400],
            }
        )

        # dropna before calculating
        valid_data = stream["watts"].dropna()
        result = calculator._time_weighted_mean(
            valid_data, stream.loc[valid_data.index]
        )

        assert not np.isnan(result)
        assert result > 0

    def test_very_large_time_gap(self, settings_with_ftp: Settings):
        """Test handling of very large time gaps."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 10000],  # Huge gap
                "watts": [200, 300, 400],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # Should still calculate without error
        assert result > 0
        assert np.isfinite(result)

    def test_subset_of_stream(self, settings_with_ftp: Settings):
        """Test time-weighted mean on subset of stream (realistic use case)."""
        calculator = MockCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4, 5],
                "watts": [100, 200, 300, 400, 500, 600],
            }
        )

        # Calculate mean for middle subset
        subset = stream.loc[2:4, "watts"]
        result = calculator._time_weighted_mean(subset, stream.loc[subset.index])

        # Should work correctly with non-contiguous indices
        assert result > 0
        assert result == pytest.approx(400.0, rel=0.1)


class TestRealWorldScenarios:
    """Test with realistic activity patterns."""

    def test_commute_with_stops(self, settings_with_ftp: Settings):
        """Test time-weighted average for commute with traffic lights."""
        calculator = MockCalculator(settings_with_ftp)

        # Simulate: 200W for 30s, stop for 20s, 200W for 30s
        stream = pd.DataFrame(
            {
                "time": [0, 30, 50, 80],
                "watts": [200, 200, 0, 200],
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # time=[0,30,50,80], diff=[NaN,30,20,30], first gets second -> [30,30,20,30]
        # weighted: (200*30 + 200*30 + 0*20 + 200*30) / (30+30+20+30)
        expected = (200 * 30 + 200 * 30 + 0 * 20 + 200 * 30) / (30 + 30 + 20 + 30)
        assert result == pytest.approx(expected, rel=1e-2)

    def test_interval_workout(
        self, realistic_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test time-weighted average with realistic interval workout."""
        calculator = MockCalculator(settings_with_ftp)

        result = calculator._time_weighted_mean(
            realistic_stream["watts"], realistic_stream
        )

        # Should calculate without error
        assert result > 0
        assert np.isfinite(result)

    def test_recovery_ride(self, settings_with_ftp: Settings):
        """Test time-weighted average for steady recovery ride."""
        calculator = MockCalculator(settings_with_ftp)

        # Steady easy power
        stream = pd.DataFrame(
            {
                "time": range(0, 1800),  # 30 minutes
                "watts": [150] * 1800,
            }
        )

        result = calculator._time_weighted_mean(stream["watts"], stream)

        # Should be exactly 150W
        assert result == pytest.approx(150.0, rel=1e-3)
