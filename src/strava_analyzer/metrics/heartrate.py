"""
Heart rate metric calculations.

This module handles all heart rate-related metrics including:
- Average/Max heart rate
- Heart rate-based Training Stress Score (hrTSS)
"""

import logging

import pandas as pd

from ..constants import TimeConstants
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class HeartRateCalculator(BaseMetricCalculator):
    """Calculates heart rate metrics from activity stream data."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate all heart rate metrics.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of HR metrics with appropriate prefix
        """
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)
        metrics = {}

        if "heartrate" not in df.columns:
            return self._get_empty_metrics(prefix)

        try:
            # For time-weighted mean, include zero values (stopped/resting periods)
            # Zeros with large time deltas correctly represent stopped time
            hr_data = df["heartrate"]
            if hr_data.empty or hr_data.max() == 0:
                return self._get_empty_metrics(prefix)

            # Use time-weighted mean for average heart rate (includes zeros)
            # For moving metrics, clip gaps to prevent filtered points from creating
            # large deltas
            metrics[f"{prefix}average_hr"] = self._time_weighted_mean(
                hr_data, df, clip_gaps=moving_only
            )

            # Max HR should still exclude zeros
            valid_hr = hr_data[hr_data > 0]
            metrics[f"{prefix}max_hr"] = (
                float(valid_hr.max()) if not valid_hr.empty else 0.0
            )

            # Calculate HR-based TSS if FTHR is configured
            if self.settings.fthr and self.settings.fthr > 0:
                hr_tss = self._calculate_hr_tss(df, moving_only)
                metrics[f"{prefix}hr_training_stress"] = hr_tss
            else:
                metrics[f"{prefix}hr_training_stress"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating HR metrics: {e}")
            return self._get_empty_metrics(prefix)

    def _calculate_hr_tss(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> float:
        """
        Calculate heart rate-based Training Stress Score.

        Args:
            stream_df: DataFrame containing heart rate data and time column
            moving_only: If True, clip gaps in time deltas

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
            # Use time-weighted mean for HR intensity (includes zeros for stopped
            # periods)
            mean_hr = self._time_weighted_mean(
                hr_series, stream_df, clip_gaps=moving_only
            )
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

    def _get_empty_metrics(self, prefix: str) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            f"{prefix}average_hr": 0.0,
            f"{prefix}max_hr": 0.0,
            f"{prefix}hr_training_stress": 0.0,
        }
