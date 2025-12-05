"""
Basic aggregated metrics calculation.

This module handles calculation of simple aggregated metrics such as:
- Average and max cadence
- Average and max speed
"""

import logging

import pandas as pd

from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class BasicMetricsCalculator(BaseMetricCalculator):
    """Calculates basic aggregated metrics from activity stream data."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate basic aggregated metrics.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of basic metrics with appropriate prefix
        """
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)
        metrics = {}

        # Cadence metrics
        cadence_metrics = self._calculate_cadence_metrics(df, prefix)
        metrics.update(cadence_metrics)

        # Speed metrics
        speed_metrics = self._calculate_speed_metrics(df, prefix)
        metrics.update(speed_metrics)

        return metrics

    def _calculate_cadence_metrics(
        self, stream_df: pd.DataFrame, prefix: str
    ) -> dict[str, float]:
        """
        Calculate cadence metrics (average and max).

        Args:
            stream_df: Filtered DataFrame containing stream data
            prefix: Metric prefix (e.g., 'raw_' or 'moving_')

        Returns:
            Dictionary of cadence metrics
        """
        metrics = {}

        if "cadence" not in stream_df.columns:
            metrics[f"{prefix}average_cadence"] = 0.0
            metrics[f"{prefix}max_cadence"] = 0.0
            return metrics

        try:
            cadence_data = stream_df["cadence"]

            # Filter out zero cadence values for calculations
            valid_cadence = cadence_data[cadence_data > 0]

            if valid_cadence.empty:
                metrics[f"{prefix}average_cadence"] = 0.0
                metrics[f"{prefix}max_cadence"] = 0.0
            else:
                # Average cadence (time-weighted)
                metrics[f"{prefix}average_cadence"] = self._time_weighted_mean(
                    cadence_data, stream_df, clip_gaps=False
                )

                # Max cadence
                metrics[f"{prefix}max_cadence"] = float(valid_cadence.max())

        except Exception as e:
            logger.warning(f"Error calculating cadence metrics: {e}")
            metrics[f"{prefix}average_cadence"] = 0.0
            metrics[f"{prefix}max_cadence"] = 0.0

        return metrics

    def _calculate_speed_metrics(
        self, stream_df: pd.DataFrame, prefix: str
    ) -> dict[str, float]:
        """
        Calculate speed metrics (average and max).

        Speed is typically stored as velocity_smooth in m/s, but we'll look
        for velocity_smooth, velocity, or speed columns.

        Args:
            stream_df: Filtered DataFrame containing stream data
            prefix: Metric prefix (e.g., 'raw_' or 'moving_')

        Returns:
            Dictionary of speed metrics
        """
        metrics = {}

        # Try different column names for speed/velocity
        speed_column = None
        for col in ["velocity_smooth", "velocity", "speed"]:
            if col in stream_df.columns:
                speed_column = col
                break

        if speed_column is None:
            metrics[f"{prefix}average_speed"] = 0.0
            metrics[f"{prefix}max_speed"] = 0.0
            return metrics

        try:
            speed_data = stream_df[speed_column]

            # Filter out zero speed values for calculations
            valid_speed = speed_data[speed_data > 0]

            if valid_speed.empty:
                metrics[f"{prefix}average_speed"] = 0.0
                metrics[f"{prefix}max_speed"] = 0.0
            else:
                # Average speed (time-weighted)
                metrics[f"{prefix}average_speed"] = self._time_weighted_mean(
                    speed_data, stream_df, clip_gaps=False
                )

                # Max speed
                metrics[f"{prefix}max_speed"] = float(valid_speed.max())

        except Exception as e:
            logger.warning(f"Error calculating speed metrics: {e}")
            metrics[f"{prefix}average_speed"] = 0.0
            metrics[f"{prefix}max_speed"] = 0.0

        return metrics
