"""
Fatigue resistance and power decay analysis.

This module provides metrics for analyzing fatigue during activities:
- Fatigue index from power decay
- First/second half power comparison
- Power sustainability metrics

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import numpy as np
import pandas as pd

from ..constants import TimeConstants, ValidationThresholds
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class FatigueCalculator(BaseMetricCalculator):
    """
    Calculates fatigue resistance metrics.

    Analyzes power decay and sustainability during activities
    to quantify fatigue resistance.
    """

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate fatigue resistance metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of fatigue metrics (no prefix)
        """
        df = stream_df
        metrics: dict[str, float] = {}

        # Only calculate for activities with power data
        if "watts" not in df.columns or df.empty:
            return metrics

        # Require minimum duration for meaningful fatigue analysis
        if len(df) < TimeConstants.MIN_DECOUPLING_DURATION:
            return metrics

        # Calculate various fatigue metrics
        fatigue_metrics = self._calculate_fatigue_index(df)
        half_comparison = self._calculate_half_comparison(df)
        sustainability = self._calculate_power_sustainability(df)

        # Combine all metrics
        metrics.update(fatigue_metrics)
        metrics.update(half_comparison)
        metrics.update(sustainability)

        return metrics

    def _calculate_fatigue_index(self, df: pd.DataFrame) -> dict[str, float]:
        """Calculate fatigue index from power decay between halves.

        Fatigue Index = (FHalf Power - SHalf Power) / FHalf Power × 100
        Uses time-weighted averaging for accurate power calculations.

        Args:
            df: Stream data with power

        Returns:
            Dictionary with fatigue index metrics
        """
        if len(df) < 120:  # Need at least 2 minutes
            return {}

        # Split into halves (consistent with power_drift calculation)
        midpoint = len(df) // 2
        first_half_df = df.iloc[:midpoint]
        second_half_df = df.iloc[midpoint:]

        # Calculate time-weighted averages for each half
        first_half_power = self._time_weighted_mean(
            first_half_df["watts"], first_half_df
        )
        second_half_power = self._time_weighted_mean(
            second_half_df["watts"], second_half_df
        )

        if first_half_power == 0 or second_half_power == 0:
            return {}

        # Fatigue index: positive value representing power loss
        fatigue_index = (
            (first_half_power - second_half_power) / first_half_power
        ) * 100

        return {
            "fatigue_index": fatigue_index,
            "initial_5min_power": first_half_power,  # backwards compat
            "final_5min_power": second_half_power,  # backwards compat
        }

    def _calculate_half_comparison(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Compare first half vs second half power using time-weighted averaging.

        Args:
            df: Stream data with power

        Returns:
            Dictionary with half comparison metrics
        """
        if len(df) < 120:  # Need at least 2 minutes
            return {}

        # Split into halves (consistent with cardiac drift calculation)
        midpoint = len(df) // 2
        first_half_df = df.iloc[:midpoint]
        second_half_df = df.iloc[midpoint:]

        # Calculate time-weighted averages for each half
        first_half_power = self._time_weighted_mean(
            first_half_df["watts"], first_half_df
        )
        second_half_power = self._time_weighted_mean(
            second_half_df["watts"], second_half_df
        )

        if first_half_power == 0 or second_half_power == 0:
            return {}

        # Calculate power drift percentage (negative = power decreasing)
        power_drift_pct = (
            (second_half_power - first_half_power) / first_half_power
        ) * 100

        # Calculate ratio
        half_power_ratio = second_half_power / first_half_power

        return {
            "first_half_power": first_half_power,
            "second_half_power": second_half_power,
            "power_drift": power_drift_pct,
            "half_power_ratio": half_power_ratio,
        }

    def _calculate_power_sustainability(self, df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate power sustainability metrics using coefficient of variation.

        Args:
            df: Stream data with power

        Returns:
            Dictionary with sustainability metrics
        """
        power = df["watts"].values

        # Filter valid power values
        valid_power = power[power > ValidationThresholds.MIN_POWER_WATTS]

        if len(valid_power) < ValidationThresholds.MIN_POWER_FOR_METRICS:
            return {}

        # Calculate coefficient of variation (CV)
        mean_power = valid_power.mean()
        std_power = valid_power.std()

        if mean_power == 0:
            return {}

        cv = (std_power / mean_power) * 100

        # Calculate power sustainability index
        # Lower CV = more sustainable power
        # PSI = 100 - CV (so higher is better)
        power_sustainability_index = max(0, 100 - cv)

        return {
            "power_coefficient_variation": cv,
            "power_sustainability_index": power_sustainability_index,
        }

    def calculate_interval_fatigue(
        self, df: pd.DataFrame, interval_duration: int = 300
    ) -> dict[str, float]:
        """
        Analyze fatigue across intervals of specified duration.

        Args:
            df: Stream data with power
            interval_duration: Duration of each interval in seconds

        Returns:
            Dictionary with interval fatigue metrics
        """
        if "watts" not in df.columns or df.empty:
            return {}

        power = df["watts"].values
        n_intervals = len(power) // interval_duration

        if n_intervals < 2:
            return {}

        interval_powers = []
        for i in range(n_intervals):
            start_idx = i * interval_duration
            end_idx = start_idx + interval_duration
            interval_power = power[start_idx:end_idx]
            valid_power = interval_power[
                interval_power > ValidationThresholds.MIN_POWER_WATTS
            ]
            if len(valid_power) > 0:
                interval_powers.append(valid_power.mean())

        if len(interval_powers) < 2:
            return {}

        # Calculate power decay across intervals
        interval_powers_arr = np.array(interval_powers)
        first_interval = interval_powers_arr[0]
        last_interval = interval_powers_arr[-1]

        decay_rate = (
            ((first_interval - last_interval) / first_interval) * 100
            if first_interval > 0
            else 0.0
        )

        # Calculate linear trend
        x = np.arange(len(interval_powers_arr))
        if len(x) > 0 and np.std(x) > 0:
            slope, _ = np.polyfit(x, interval_powers_arr, 1)
            # Normalize slope by mean power
            normalized_slope = (
                (slope / interval_powers_arr.mean()) * 100
                if interval_powers_arr.mean() > 0
                else 0.0
            )
        else:
            normalized_slope = 0.0

        return {
            f"interval_{interval_duration}s_decay_rate": decay_rate,
            f"interval_{interval_duration}s_power_trend": normalized_slope,
            f"interval_{interval_duration}s_first_power": first_interval,
            f"interval_{interval_duration}s_last_power": last_interval,
        }
