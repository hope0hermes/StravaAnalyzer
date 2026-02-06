"""
Basic aggregated metrics calculation.

This module handles calculation of simple aggregated metrics such as:
- Average and max cadence
- Average and max speed

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import pandas as pd

from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class BasicMetricsCalculator(BaseMetricCalculator):
    """Calculates basic aggregated metrics from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate basic aggregated metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of basic metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        # Cadence metrics
        cadence_metrics = self._calculate_cadence_metrics(stream_df)
        metrics.update(cadence_metrics)

        # Speed metrics
        speed_metrics = self._calculate_speed_metrics(stream_df)
        metrics.update(speed_metrics)

        return metrics

    def _calculate_cadence_metrics(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate cadence metrics (average and max).

        Args:
            stream_df: Filtered DataFrame containing stream data

        Returns:
            Dictionary of cadence metrics
        """
        metrics: dict[str, float] = {}

        if "cadence" not in stream_df.columns:
            metrics["average_cadence"] = 0.0
            metrics["max_cadence"] = 0.0
            return metrics

        try:
            cadence_data = stream_df["cadence"]

            # Filter out zero cadence values for calculations
            valid_cadence = cadence_data[cadence_data > 0]

            if valid_cadence.empty:
                metrics["average_cadence"] = 0.0
                metrics["max_cadence"] = 0.0
            else:
                # Average cadence (time-weighted)
                metrics["average_cadence"] = self._time_weighted_mean(
                    cadence_data, stream_df
                )

                # Max cadence
                metrics["max_cadence"] = float(valid_cadence.max())

        except Exception as e:
            logger.warning(f"Error calculating cadence metrics: {e}")
            metrics["average_cadence"] = 0.0
            metrics["max_cadence"] = 0.0

        return metrics

    def _calculate_speed_metrics(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate speed metrics (average and max).

        Speed is typically stored as velocity_smooth in m/s, but we'll look
        for velocity_smooth, velocity, or speed columns.

        Args:
            stream_df: Filtered DataFrame containing stream data

        Returns:
            Dictionary of speed metrics
        """
        metrics: dict[str, float] = {}

        # Try different column names for speed/velocity
        speed_column = None
        for col in ["velocity_smooth", "velocity", "speed"]:
            if col in stream_df.columns:
                speed_column = col
                break

        if speed_column is None:
            metrics["average_speed"] = 0.0
            metrics["max_speed"] = 0.0
            return metrics

        try:
            speed_data = stream_df[speed_column]

            # Filter out zero speed values for calculations
            valid_speed = speed_data[speed_data > 0]

            if valid_speed.empty:
                metrics["average_speed"] = 0.0
                metrics["max_speed"] = 0.0
            else:
                # Average speed (time-weighted)
                metrics["average_speed"] = self._time_weighted_mean(
                    speed_data, stream_df
                )

                # Max speed
                metrics["max_speed"] = float(valid_speed.max())

        except Exception as e:
            logger.warning(f"Error calculating speed metrics: {e}")
            metrics["average_speed"] = 0.0
            metrics["max_speed"] = 0.0

        return metrics
