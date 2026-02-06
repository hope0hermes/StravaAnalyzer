"""
Efficiency and decoupling metric calculations.

This module handles efficiency metrics including:
- Efficiency Factor (EF)
- Power:HR decoupling
- Variability Index (VI)

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import numpy as np
import pandas as pd

from ..constants import TimeConstants
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class EfficiencyCalculator(BaseMetricCalculator):
    """Calculates efficiency and decoupling metrics."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all efficiency metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of efficiency metrics (no prefix)
        """
        has_power = "watts" in stream_df.columns
        has_hr = "heartrate" in stream_df.columns

        if not has_power or not has_hr:
            return self._get_empty_metrics()

        try:
            metrics: dict[str, float] = {}

            # Efficiency Factor
            ef = self._calculate_efficiency_factor(stream_df)
            metrics["efficiency_factor"] = ef

            # Decoupling
            decoupling, first_half_ef, second_half_ef = self._calculate_decoupling(
                stream_df
            )
            metrics["power_hr_decoupling"] = decoupling
            metrics["first_half_ef"] = first_half_ef
            metrics["second_half_ef"] = second_half_ef

            # Variability Index
            vi = self._calculate_variability_index(stream_df)
            metrics["variability_index"] = vi

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating efficiency metrics: {e}")
            return self._get_empty_metrics()

    def _calculate_normalized_power(self, stream_df: pd.DataFrame) -> float:
        """Calculate normalized power for efficiency calculations."""
        if "watts" not in stream_df.columns:
            return 0.0

        power_data = stream_df["watts"]
        valid_power = power_data[power_data > 0]
        if (
            valid_power.empty
            or len(valid_power) < TimeConstants.NORMALIZED_POWER_WINDOW
        ):
            return 0.0

        try:
            clean_power = valid_power.fillna(0)
            rolled = clean_power.rolling(
                window=TimeConstants.NORMALIZED_POWER_WINDOW, min_periods=1
            ).mean()
            rolled_4 = rolled**4

            # Time-weighted mean of fourth powers
            time_deltas = self._calculate_time_deltas(stream_df.loc[rolled_4.index])
            weighted_fourth = (rolled_4 * time_deltas).sum() / time_deltas.sum()

            np_value = float(weighted_fourth**0.25)
            return np_value if np.isfinite(np_value) else 0.0
        except Exception:
            return 0.0

    def _calculate_efficiency_factor(self, stream_df: pd.DataFrame) -> float:
        """Calculate Efficiency Factor (NP / avg HR)."""
        if "watts" not in stream_df.columns or "heartrate" not in stream_df.columns:
            return 0.0

        try:
            np_value = self._calculate_normalized_power(stream_df)
            hr_data = stream_df["heartrate"]
            avg_hr = self._time_weighted_mean(hr_data, stream_df)

            if np_value > 0 and avg_hr > 0:
                ef = np_value / avg_hr
                return ef if np.isfinite(ef) else 0.0
            return 0.0
        except Exception:
            return 0.0

    def _calculate_decoupling(
        self, stream_df: pd.DataFrame
    ) -> tuple[float, float, float]:
        """Calculate power:HR decoupling percentage."""
        if len(stream_df) < TimeConstants.MIN_ROLLING_CALCULATION:
            return 0.0, 0.0, 0.0

        try:
            # Split into halves
            midpoint = len(stream_df) // 2
            first_half = stream_df.iloc[:midpoint]
            second_half = stream_df.iloc[midpoint:]

            # Calculate EF for each half
            first_ef = self._calculate_efficiency_factor(first_half)
            second_ef = self._calculate_efficiency_factor(second_half)

            # Calculate decoupling
            if first_ef > 0:
                decoupling = ((second_ef - first_ef) / first_ef) * 100
            else:
                decoupling = 0.0

            return float(decoupling), float(first_ef), float(second_ef)
        except Exception:
            return 0.0, 0.0, 0.0

    def _calculate_variability_index(self, stream_df: pd.DataFrame) -> float:
        """Calculate Variability Index (NP / AP ratio)."""
        if "watts" not in stream_df.columns:
            return 0.0

        power_data = stream_df["watts"]
        if power_data.empty or power_data.max() == 0:
            return 0.0

        try:
            np_value = self._calculate_normalized_power(stream_df)
            ap = self._time_weighted_mean(power_data, stream_df)

            if np_value > 0 and ap > 0:
                vi = np_value / ap
                return vi if np.isfinite(vi) else 0.0
            return 0.0
        except Exception:
            return 0.0

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return dict of zero-valued metrics when no valid data."""
        return {
            "efficiency_factor": 0.0,
            "power_hr_decoupling": 0.0,
            "first_half_ef": 0.0,
            "second_half_ef": 0.0,
            "variability_index": 0.0,
        }
