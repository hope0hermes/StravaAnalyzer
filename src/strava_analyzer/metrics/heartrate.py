"""
Heart rate metric calculations.

This module handles all heart rate-related metrics including:
- Average/Max heart rate
- Heart rate-based Training Stress Score (hrTSS)

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import pandas as pd

from ..constants import TimeConstants
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class HeartRateCalculator(BaseMetricCalculator):
    """Calculates heart rate metrics from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all heart rate metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of HR metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        if "heartrate" not in stream_df.columns:
            return self._get_empty_metrics()

        try:
            hr_data = stream_df["heartrate"]
            if hr_data.empty or hr_data.max() == 0:
                return self._get_empty_metrics()

            # Use time-weighted mean for average heart rate
            metrics["average_hr"] = self._time_weighted_mean(hr_data, stream_df)

            # Max HR should still exclude zeros
            valid_hr = hr_data[hr_data > 0]
            metrics["max_hr"] = (
                float(valid_hr.max()) if not valid_hr.empty else 0.0
            )

            # Calculate HR-based TSS if FTHR is configured
            if self.settings.fthr and self.settings.fthr > 0:
                hr_tss = self._calculate_hr_tss(stream_df)
                metrics["hr_training_stress"] = hr_tss
            else:
                metrics["hr_training_stress"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating HR metrics: {e}")
            return self._get_empty_metrics()

    def _calculate_hr_tss(self, stream_df: pd.DataFrame) -> float:
        """
        Calculate heart rate-based Training Stress Score.

        Args:
            stream_df: DataFrame containing heart rate data and time column

        Returns:
            HR-based TSS value
        """
        if "heartrate" not in stream_df.columns:
            return 0.0

        hr_series = stream_df["heartrate"]
        valid_hr = hr_series[hr_series > 0]
        if valid_hr.empty:
            return 0.0

        try:
            # Use time-weighted mean for HR intensity
            mean_hr = self._time_weighted_mean(hr_series, stream_df)
            hr_intensity = mean_hr / self.settings.fthr

            # Use actual duration
            duration_seconds = self._get_total_duration(stream_df)

            hr_tss = (
                (hr_intensity**2)
                * duration_seconds
                / TimeConstants.SECONDS_PER_HOUR
                * 100
            )
            return float(hr_tss)
        except Exception as e:
            logger.warning(f"Error in hrTSS calculation: {e}")
            return 0.0

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            "average_hr": 0.0,
            "max_hr": 0.0,
            "hr_training_stress": 0.0,
        }

