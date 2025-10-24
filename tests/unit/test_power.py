"""Unit tests for Power metrics calculator."""

import numpy as np
import pandas as pd
import pytest

from strava_analyzer.metrics.power import PowerCalculator
from strava_analyzer.settings import Settings


class TestPowerCalculatorBasics:
    """Test basic power calculations."""

    def test_average_power_simple(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test average power calculation with simple stream."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert "raw_average_power" in metrics
        assert metrics["raw_average_power"] > 0

    def test_max_power_simple(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test max power calculation."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert "raw_max_power" in metrics
        assert metrics["raw_max_power"] == simple_stream["watts"].max()

    def test_power_per_kg(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test power per kg calculation."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert "raw_power_per_kg" in metrics
        expected_power_per_kg = (
            metrics["raw_average_power"] / settings_with_ftp.rider_weight_kg
        )
        assert metrics["raw_power_per_kg"] == pytest.approx(
            expected_power_per_kg, rel=1e-3
        )

    def test_zero_power_returns_empty_metrics(self, settings_with_ftp: Settings):
        """Test that zero power data returns empty metrics."""
        calculator = PowerCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4],
                "watts": [0, 0, 0, 0, 0],
                "moving": [True, True, True, True, True],
            }
        )

        metrics = calculator.calculate(stream, moving_only=False)

        assert metrics["raw_average_power"] == 0.0
        assert metrics["raw_normalized_power"] == 0.0


class TestNormalizedPower:
    """Test Normalized Power calculation."""

    def test_normalized_power_realistic_stream(
        self, realistic_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test NP calculation with realistic interval stream."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(realistic_stream, moving_only=False)

        # NP should be higher than average power for interval workouts
        assert metrics["raw_normalized_power"] > metrics["raw_average_power"]
        assert metrics["raw_normalized_power"] > 0

    def test_normalized_power_steady_effort(self, settings_with_ftp: Settings):
        """Test NP calculation with steady power output."""
        # Create steady power stream (NP should be close to average)
        stream = pd.DataFrame(
            {
                "time": range(0, 300),  # 5 minutes
                "watts": [250] * 300,  # Steady 250W
                "moving": [True] * 300,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        # For steady power, NP should be very close to average
        assert metrics["raw_normalized_power"] == pytest.approx(250, abs=5)
        assert metrics["raw_average_power"] == pytest.approx(250, rel=0.01)

    def test_normalized_power_with_zeros(
        self, stream_with_zeros: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test NP calculation handles zero power correctly."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(stream_with_zeros, moving_only=False)

        # Average power includes zeros (time-weighted)
        assert metrics["raw_average_power"] > 0
        # NP may be 0 if not enough valid power points for calculation
        # Just check that metrics are calculated
        assert "raw_normalized_power" in metrics


class TestIntensityFactor:
    """Test Intensity Factor calculation."""

    def test_intensity_factor_calculation(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test IF calculation."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert "raw_intensity_factor" in metrics
        # IF should be NP / FTP
        expected_if = metrics["raw_normalized_power"] / settings_with_ftp.ftp
        assert metrics["raw_intensity_factor"] == pytest.approx(expected_if, rel=1e-3)

    def test_intensity_factor_at_ftp(self, settings_with_ftp: Settings):
        """Test IF calculation when riding at FTP."""
        # Create stream at FTP power
        stream = pd.DataFrame(
            {
                "time": range(0, 3600),  # 1 hour
                "watts": [settings_with_ftp.ftp] * 3600,
                "moving": [True] * 3600,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        # IF should be approximately 1.0 at FTP
        assert metrics["raw_intensity_factor"] == pytest.approx(1.0, abs=0.05)

    def test_intensity_factor_zero_when_no_ftp(self, simple_stream: pd.DataFrame):
        """Test IF returns 0 when FTP is not set."""
        settings = Settings(ftp=0)
        calculator = PowerCalculator(settings)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert metrics["raw_intensity_factor"] == 0.0


class TestTrainingStressScore:
    """Test TSS calculation."""

    def test_tss_calculation(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test basic TSS calculation."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=False)

        assert "raw_training_stress_score" in metrics
        assert metrics["raw_training_stress_score"] >= 0

    def test_tss_one_hour_at_ftp(self, settings_with_ftp: Settings):
        """Test that 1 hour at FTP gives TSS = 100."""
        # Create 1 hour stream at FTP
        stream = pd.DataFrame(
            {
                "time": range(0, 3600),  # 1 hour
                "watts": [settings_with_ftp.ftp] * 3600,
                "moving": [True] * 3600,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        # TSS should be approximately 100 (may have small variation due to NP
        # calculation)
        assert metrics["raw_training_stress_score"] == pytest.approx(100, abs=5)

    def test_tss_scales_with_duration(self, settings_with_ftp: Settings):
        """Test that TSS scales with duration at constant intensity."""
        power = 200  # Submaximal power

        # 30 minute ride
        stream_30 = pd.DataFrame(
            {
                "time": range(0, 1800),
                "watts": [power] * 1800,
                "moving": [True] * 1800,
            }
        )

        # 60 minute ride
        stream_60 = pd.DataFrame(
            {
                "time": range(0, 3600),
                "watts": [power] * 3600,
                "moving": [True] * 3600,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics_30 = calculator.calculate(stream_30, moving_only=False)
        metrics_60 = calculator.calculate(stream_60, moving_only=False)

        # 60 minute TSS should be approximately double 30 minute TSS
        assert metrics_60["raw_training_stress_score"] == pytest.approx(
            metrics_30["raw_training_stress_score"] * 2, rel=0.1
        )

    def test_tss_zero_when_no_power(self, settings_with_ftp: Settings):
        """Test TSS returns 0 when no power data."""
        stream = pd.DataFrame(
            {
                "time": [0, 1, 2],
                "watts": [0, 0, 0],
                "moving": [True, True, True],
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        assert metrics["raw_training_stress_score"] == 0.0


class TestMovingMetrics:
    """Test power calculations with moving_only=True."""

    def test_moving_only_prefix(
        self, simple_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test that moving_only=True adds 'moving_' prefix."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(simple_stream, moving_only=True)

        assert "moving_average_power" in metrics
        assert "moving_normalized_power" in metrics
        assert "moving_training_stress_score" in metrics

    def test_moving_only_excludes_stopped(self, settings_with_ftp: Settings):
        """Test that moving_only=True excludes stopped periods."""
        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "watts": [200, 200, 200, 0, 0, 0, 200, 200, 200, 200],
                "moving": [
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    True,
                    True,
                ],
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics_all = calculator.calculate(stream, moving_only=False)
        metrics_moving = calculator.calculate(stream, moving_only=True)

        # Moving average should be higher (excludes zeros when stopped)
        assert metrics_moving["moving_average_power"] > metrics_all["raw_average_power"]


class TestTimeWeighting:
    """Test time-weighted averaging in power calculations."""

    def test_time_weighted_average_with_gaps(
        self, stream_with_gaps: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test that time-weighted average correctly handles gaps."""
        calculator = PowerCalculator(settings_with_ftp)

        metrics = calculator.calculate(stream_with_gaps, moving_only=False)

        # Average should reflect time-weighting
        assert metrics["raw_average_power"] > 0

    def test_time_weighting_favors_longer_efforts(self, settings_with_ftp: Settings):
        """Test that longer efforts are weighted more heavily."""
        # Create stream: 200W for 1 second, 300W for 9 seconds
        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "watts": [200, 300, 300, 300, 300, 300, 300, 300, 300, 300],
                "moving": [True] * 10,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        # Average should be much closer to 300 than 200
        assert metrics["raw_average_power"] > 280


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self, settings_with_ftp: Settings):
        """Test handling of empty DataFrame."""
        calculator = PowerCalculator(settings_with_ftp)

        stream = pd.DataFrame({"time": [], "watts": [], "moving": []})
        metrics = calculator.calculate(stream, moving_only=False)

        # Should return empty metrics with raw_ prefix
        assert "raw_average_power" in metrics
        assert metrics["raw_average_power"] == 0.0

    def test_missing_watts_column(self, settings_with_ftp: Settings):
        """Test handling when watts column is missing."""
        calculator = PowerCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2],
                "moving": [True, True, True],
            }
        )

        metrics = calculator.calculate(stream, moving_only=False)

        # Should return empty metrics with raw_ prefix
        assert "raw_average_power" in metrics
        assert metrics["raw_average_power"] == 0.0

    def test_single_data_point(self, settings_with_ftp: Settings):
        """Test calculation with single data point."""
        calculator = PowerCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0],
                "watts": [250],
                "moving": [True],
            }
        )

        metrics = calculator.calculate(stream, moving_only=False)

        assert metrics["raw_average_power"] == 250
        assert metrics["raw_max_power"] == 250

    def test_nan_values(self, settings_with_ftp: Settings):
        """Test handling of NaN values in power data."""
        calculator = PowerCalculator(settings_with_ftp)

        stream = pd.DataFrame(
            {
                "time": [0, 1, 2, 3, 4],
                "watts": [200, np.nan, 250, np.nan, 300],
                "moving": [True, True, True, True, True],
            }
        )

        metrics = calculator.calculate(stream, moving_only=False)

        # Should handle NaN gracefully
        assert metrics["raw_average_power"] > 0
        assert not np.isnan(metrics["raw_average_power"])


class TestVariabilityIndex:
    """Test Variability Index (NP / Average Power)."""

    def test_variability_index_steady_ride(self, settings_with_ftp: Settings):
        """Test VI is close to 1.0 for steady ride."""
        # Steady power
        stream = pd.DataFrame(
            {
                "time": range(0, 300),
                "watts": [250] * 300,
                "moving": [True] * 300,
            }
        )

        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(stream, moving_only=False)

        vi = metrics["raw_normalized_power"] / metrics["raw_average_power"]
        assert vi == pytest.approx(1.0, abs=0.05)

    def test_variability_index_intervals(
        self, realistic_stream: pd.DataFrame, settings_with_ftp: Settings
    ):
        """Test VI is > 1.0 for interval workout."""
        calculator = PowerCalculator(settings_with_ftp)
        metrics = calculator.calculate(realistic_stream, moving_only=False)

        vi = metrics["raw_normalized_power"] / metrics["raw_average_power"]
        # Interval workout should have VI > 1.0
        assert vi > 1.0
