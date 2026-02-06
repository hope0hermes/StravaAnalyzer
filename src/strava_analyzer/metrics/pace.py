"""
Pace-based metric calculations for running activities.

This module handles running-specific metrics including:
- Average/Max speed
- Normalized Graded Pace (NGP)

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import pandas as pd

from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class PaceCalculator(BaseMetricCalculator):
    """Calculates pace-based metrics from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all pace metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of pace metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        if "velocity_smooth" not in stream_df.columns:
            return self._get_empty_metrics()

        try:
            valid_velocity = stream_df["velocity_smooth"][
                stream_df["velocity_smooth"] > 0
            ]
            if valid_velocity.empty:
                return self._get_empty_metrics()

            metrics["average_speed"] = float(valid_velocity.mean())
            metrics["max_speed"] = float(valid_velocity.max())

            # Calculate NGP if grade data available
            if "grade_smooth" in stream_df.columns:
                ngp = self._calculate_ngp(
                    stream_df["velocity_smooth"], stream_df["grade_smooth"]
                )
                metrics["normalized_graded_pace"] = ngp
            else:
                metrics["normalized_graded_pace"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating pace metrics: {e}")
            return self._get_empty_metrics()

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

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            "average_speed": 0.0,
            "max_speed": 0.0,
            "normalized_graded_pace": 0.0,
        }
