"""
Pace-based metric calculations for running activities.

This module handles running-specific metrics including:
- Average/Max speed
- Normalized Graded Pace (NGP)
"""

import logging

import pandas as pd

from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class PaceCalculator(BaseMetricCalculator):
    """Calculates pace-based metrics from activity stream data."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate all pace metrics.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of pace metrics with appropriate prefix
        """
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)
        metrics = {}

        if "velocity_smooth" not in df.columns:
            return self._get_empty_metrics(prefix)

        try:
            valid_velocity = df["velocity_smooth"][df["velocity_smooth"] > 0]
            if valid_velocity.empty:
                return self._get_empty_metrics(prefix)

            metrics[f"{prefix}average_speed"] = float(valid_velocity.mean())
            metrics[f"{prefix}max_speed"] = float(valid_velocity.max())

            # Calculate NGP if grade data available
            if "grade_smooth" in df.columns:
                ngp = self._calculate_ngp(df["velocity_smooth"], df["grade_smooth"])
                metrics[f"{prefix}normalized_graded_pace"] = ngp
            else:
                metrics[f"{prefix}normalized_graded_pace"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating pace metrics: {e}")
            return self._get_empty_metrics(prefix)

    def _calculate_ngp(
        self, velocity_series: pd.Series, grade_series: pd.Series
    ) -> float:
        """
        Calculate Normalized Graded Pace.

        Args:
            velocity_series: Velocity data
            grade_series: Grade/gradient data

        Returns:
            Normalized graded pace value
        """
        try:
            # Apply grade adjustment factor
            grade_factor = 1 + (
                grade_series * self.settings.grade_adjustment.uphill_factor
            )
            adjusted_pace = velocity_series * grade_factor
            return float(adjusted_pace.mean())
        except Exception as e:
            logger.warning(f"Error in NGP calculation: {e}")
            return 0.0

    def _get_empty_metrics(self, prefix: str) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            f"{prefix}average_speed": 0.0,
            f"{prefix}max_speed": 0.0,
            f"{prefix}normalized_graded_pace": 0.0,
        }
