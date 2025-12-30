"""
Climbing-specific metric calculations.

This module handles climbing-related metrics including:
- VAM (Velocità Ascensionale Media)
- Climbing time and distance
- Power on climbs
- Gradient analysis
"""

import logging

import pandas as pd

from ..constants import ValidationThresholds
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class ClimbingCalculator(BaseMetricCalculator):
    """Calculates climbing-specific metrics from activity stream data."""

    MIN_CLIMB_GRADIENT = 2.0  # Minimum gradient (%) to consider as climbing
    POWER_GRADIENT_THRESHOLD = 4.0  # Gradient threshold for power on climbs

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all climbing metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of climbing metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        # Check for required columns
        if "altitude" not in stream_df.columns or "time" not in stream_df.columns:
            return self._get_empty_metrics()

        try:
            # Calculate VAM and climbing time
            vam, climbing_time = self._calculate_vam(stream_df)
            metrics["vam"] = vam
            metrics["climbing_time"] = climbing_time

            # Calculate power on climbs (requires both gradient and power)
            if "grade_smooth" in stream_df.columns and "watts" in stream_df.columns:
                climbing_power, climbing_power_per_kg = self._calculate_climbing_power(
                    stream_df
                )
                metrics["climbing_power"] = climbing_power
                metrics["climbing_power_per_kg"] = climbing_power_per_kg
            else:
                metrics["climbing_power"] = 0.0
                metrics["climbing_power_per_kg"] = 0.0

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating climbing metrics: {e}")
            return self._get_empty_metrics()

    def _calculate_vam(self, stream_df: pd.DataFrame) -> tuple[float, float]:
        """
        Calculate VAM (Velocità Ascensionale Media) - vertical ascent rate.

        VAM = (elevation_gain / climbing_time) * 3600 (m/h)

        Args:
            stream_df: DataFrame with altitude and time columns

        Returns:
            Tuple of (VAM in m/h, climbing_time in seconds)
        """
        # Identify climbing segments (positive gradient)
        df = stream_df.copy()

        # Calculate elevation change
        df["altitude_diff"] = df["altitude"].diff().fillna(0)

        # Only consider positive elevation changes
        climbing_mask = df["altitude_diff"] > 0

        if not climbing_mask.any():
            return 0.0, 0.0

        # Calculate total elevation gain and time spent climbing
        elevation_gain = df.loc[climbing_mask, "altitude_diff"].sum()
        climbing_time = climbing_mask.sum()  # Number of seconds climbing

        if climbing_time == 0:
            return 0.0, 0.0

        # VAM in meters per hour
        vam = (elevation_gain / climbing_time) * 3600

        return float(vam), float(climbing_time)

    def _calculate_climbing_power(
        self, stream_df: pd.DataFrame
    ) -> tuple[float, float]:
        """
        Calculate average power on significant climbs (gradient > threshold).

        Args:
            stream_df: DataFrame with grade_smooth and watts columns

        Returns:
            Tuple of (avg_power on climbs, avg_power/kg on climbs)
        """
        # Identify steep climbing sections
        climbing_mask = stream_df["grade_smooth"] > self.POWER_GRADIENT_THRESHOLD

        if not climbing_mask.any():
            return 0.0, 0.0

        # Get power data during climbs
        climbing_power_data = stream_df.loc[climbing_mask, "watts"]

        # Filter out zero/invalid power values
        valid_power = climbing_power_data[climbing_power_data > 0]

        if valid_power.empty:
            return 0.0, 0.0

        avg_climbing_power = float(valid_power.mean())
        avg_climbing_power_per_kg = avg_climbing_power / self.settings.rider_weight_kg

        return avg_climbing_power, avg_climbing_power_per_kg

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return empty metrics dict with default values."""
        return {
            "vam": 0.0,
            "climbing_time": 0.0,
            "climbing_power": 0.0,
            "climbing_power_per_kg": 0.0,
        }
