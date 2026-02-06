"""
Power-based metric calculations.

This module handles all power-related metrics including:
- Normalized Power (NP)
- Intensity Factor (IF)
- Training Stress Score (TSS)
- Average/Max Power
- Power per kg

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import numpy as np
import pandas as pd

from ..constants import TimeConstants, ValidationThresholds
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class PowerCalculator(BaseMetricCalculator):
    """Calculates power-based metrics from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all power metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of power metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        if "watts" not in stream_df.columns:
            return self._get_empty_metrics()

        try:
            # Basic power metrics
            power_data = stream_df["watts"]
            if power_data.empty or power_data.max() == 0:
                return self._get_empty_metrics()

            # Use time-weighted mean for average power
            avg_power = self._time_weighted_mean(power_data, stream_df)
            metrics["average_power"] = avg_power

            # Max power should still exclude zeros
            valid_power = power_data[power_data > 0]
            metrics["max_power"] = (
                float(valid_power.max()) if not valid_power.empty else 0.0
            )
            metrics["power_per_kg"] = float(avg_power / self.settings.rider_weight_kg)

            # Normalized Power (uses time-weighted rolling average)
            normalized_power = self._calculate_normalized_power(stream_df)
            metrics["normalized_power"] = normalized_power

            # Intensity Factor and TSS
            if normalized_power > 0 and self.settings.ftp > 0:
                intensity_factor = normalized_power / self.settings.ftp
                metrics["intensity_factor"] = intensity_factor

                # TSS calculation using actual duration
                duration_seconds = self._get_total_duration(stream_df)
                tss = (
                    (normalized_power * intensity_factor * duration_seconds)
                    / (self.settings.ftp * TimeConstants.SECONDS_PER_HOUR)
                    * 100
                )
                metrics["training_stress_score"] = float(tss)
            else:
                metrics["intensity_factor"] = 0.0
                metrics["training_stress_score"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating power metrics: {e}")
            return self._get_empty_metrics()

    def _calculate_normalized_power(self, stream_df: pd.DataFrame) -> float:
        """
        Calculate Normalized Power using 30-second rolling average method.

        Args:
            stream_df: DataFrame containing power data and time column

        Returns:
            Normalized Power value
        """
        if "watts" not in stream_df.columns:
            return 0.0

        power_series = stream_df["watts"]
        valid_power = power_series[power_series > 0]
        if (
            valid_power.empty
            or len(valid_power) < ValidationThresholds.MIN_POWER_FOR_METRICS
        ):
            return 0.0

        try:
            # Use 30-second rolling window
            rolling_avg = valid_power.rolling(
                window=TimeConstants.NORMALIZED_POWER_WINDOW, min_periods=1
            ).mean()

            # Calculate fourth power and time-weighted mean
            fourth_power = rolling_avg**4

            # Time-weighted mean of fourth powers
            time_deltas = self._calculate_time_deltas(stream_df.loc[fourth_power.index])
            weighted_fourth = (fourth_power * time_deltas).sum() / time_deltas.sum()

            np_value = float(weighted_fourth**0.25)
            return np_value if np.isfinite(np_value) else 0.0
        except Exception as e:
            logger.warning(f"Error in NP calculation: {e}")
            return 0.0

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            "average_power": 0.0,
            "max_power": 0.0,
            "power_per_kg": 0.0,
            "normalized_power": 0.0,
            "intensity_factor": 0.0,
            "training_stress_score": 0.0,
        }
