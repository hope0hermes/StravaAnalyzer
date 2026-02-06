"""
Training Intensity Distribution (TID) analysis.

This module provides comprehensive TID metrics including:
- Time-in-zone distributions
- Polarization analysis
- TID ratios for various zone models

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging
from typing import Literal

import pandas as pd

from ..constants import HeartRateZoneThresholds
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class TIDCalculator(BaseMetricCalculator):
    """
    Calculates Training Intensity Distribution metrics.

    Provides detailed analysis of training intensity patterns including
    polarization analysis and zone distribution ratios.
    """

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate TID metrics using time-weighted calculations.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of TID metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        # Calculate TID metrics based on available data
        if "watts" in stream_df.columns and self.settings.ftp > 0:
            power_tid = self._calculate_power_tid(stream_df["watts"], stream_df)
            metrics.update(power_tid)

        if "heartrate" in stream_df.columns and self.settings.fthr > 0:
            hr_tid = self._calculate_hr_tid(stream_df["heartrate"], stream_df)
            metrics.update(hr_tid)

        return metrics

    def _calculate_power_tid(
        self, power_series: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Calculate TID metrics based on power zones using time-weighted calculations.

        Uses 3-zone model:
        - Zone 1 (Low): < 76% FTP (combines Z1 + Z2)
        - Zone 2 (Moderate): 76-90% FTP (Z3)
        - Zone 3 (High): > 90% FTP (combines Z4-Z7)

        Args:
            power_series: Power data
            stream_df: Full DataFrame for time delta calculation

        Returns:
            Dictionary of TID metrics
        """
        if power_series.empty:
            return {}

        # Get time deltas for time-weighted calculation
        time_deltas = self._calculate_time_deltas(stream_df)
        total_time = time_deltas.sum()

        if total_time == 0:
            return {}

        ftp = self.settings.ftp

        # 3-zone TID model
        zone1_threshold = 0.76 * ftp  # Low intensity
        zone2_threshold = 0.90 * ftp  # Moderate intensity

        # Time-weighted zone calculations
        zone1_mask = power_series < zone1_threshold
        zone2_mask = (power_series >= zone1_threshold) & (
            power_series < zone2_threshold
        )
        zone3_mask = power_series >= zone2_threshold

        zone1_time = time_deltas[zone1_mask].sum()
        zone2_time = time_deltas[zone2_mask].sum()
        zone3_time = time_deltas[zone3_mask].sum()

        # Calculate percentages
        z1_pct = (zone1_time / total_time) * 100
        z2_pct = (zone2_time / total_time) * 100
        z3_pct = (zone3_time / total_time) * 100

        # Calculate polarization index
        # PI = (Z1 + Z3) / Z2
        # Higher values indicate more polarized training
        polarization_index = (z1_pct + z3_pct) / z2_pct if z2_pct > 0 else 0.0

        # Calculate training distribution ratio (TDR)
        # TDR = Z1 / Z3
        # Values > 2.0 are considered polarized
        tdr = z1_pct / z3_pct if z3_pct > 0 else 0.0

        return {
            "power_tid_z1_percentage": z1_pct,
            "power_tid_z2_percentage": z2_pct,
            "power_tid_z3_percentage": z3_pct,
            "power_polarization_index": polarization_index,
            "power_tdr": tdr,
        }

    def _calculate_hr_tid(
        self, hr_series: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """Calculate HR-based TID metrics using time-weighted calculations.

        Uses 3-zone model:
        - Zone 1 (Low): < 82% FTHR (Z1)
        - Zone 2 (Moderate): 82-94% FTHR (Z2 + Z3)
        - Zone 3 (High): > 94% FTHR (Z4 + Z5)

        Args:
            hr_series: Heart rate data
            stream_df: Full DataFrame for time delta calculation

        Returns:
            Dictionary of TID metrics
        """
        if hr_series.empty:
            return {}

        # Get time deltas for time-weighted calculation
        time_deltas = self._calculate_time_deltas(stream_df)
        total_time = time_deltas.sum()

        if total_time == 0:
            return {}

        fthr = self.settings.fthr

        # 3-zone TID model based on HR
        zone1_threshold = HeartRateZoneThresholds.ZONE_1_MAX * fthr  # 82% FTHR
        zone2_threshold = HeartRateZoneThresholds.ZONE_3_MAX * fthr  # 94% FTHR

        # Time-weighted zone calculations
        zone1_mask = hr_series < zone1_threshold
        zone2_mask = (hr_series >= zone1_threshold) & (hr_series < zone2_threshold)
        zone3_mask = hr_series >= zone2_threshold

        zone1_time = time_deltas[zone1_mask].sum()
        zone2_time = time_deltas[zone2_mask].sum()
        zone3_time = time_deltas[zone3_mask].sum()

        # Calculate percentages
        z1_pct = (zone1_time / total_time) * 100
        z2_pct = (zone2_time / total_time) * 100
        z3_pct = (zone3_time / total_time) * 100

        # Calculate polarization index
        polarization_index = (z1_pct + z3_pct) / z2_pct if z2_pct > 0 else 0.0

        # Calculate training distribution ratio
        tdr = z1_pct / z3_pct if z3_pct > 0 else 0.0

        return {
            "hr_tid_z1_percentage": z1_pct,
            "hr_tid_z2_percentage": z2_pct,
            "hr_tid_z3_percentage": z3_pct,
            "hr_polarization_index": polarization_index,
            "hr_tdr": tdr,
        }

    def calculate_tid_classification(
        self,
        z1_pct: float,
        z2_pct: float,
        z3_pct: float,
    ) -> Literal["polarized", "pyramidal", "threshold"]:
        """
        Classify training distribution pattern.

        Args:
            z1_pct: Percentage time in zone 1 (low intensity)
            z2_pct: Percentage time in zone 2 (moderate intensity)
            z3_pct: Percentage time in zone 3 (high intensity)

        Returns:
            Training distribution classification
        """
        # Polarized: High Z1 (>75%), low Z2 (<10%), moderate Z3
        if z1_pct > 75 and z2_pct < 10:
            return "polarized"

        # Pyramidal: Descending Z1 > Z2 > Z3
        if z1_pct > z2_pct > z3_pct:
            return "pyramidal"

        # Threshold: High Z2/Z3
        return "threshold"

    def calculate_weekly_tid(self, activities_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate weekly TID from multiple activities.

        NOTE: Data is expected to be from a single mode (raw OR moving).
        Column names no longer have prefixes since DataFrames are pre-split.

        Args:
            activities_df: DataFrame with activity metrics (single mode)

        Returns:
            Weekly aggregated TID metrics
        """
        tid_cols = {
            "power": [
                "power_tid_z1_percentage",
                "power_tid_z2_percentage",
                "power_tid_z3_percentage",
            ],
            "hr": [
                "hr_tid_z1_percentage",
                "hr_tid_z2_percentage",
                "hr_tid_z3_percentage",
            ],
        }

        weekly_metrics = {}

        for metric_type, cols in tid_cols.items():
            # Check if columns exist
            if not all(col in activities_df.columns for col in cols):
                continue

            # Weight by moving_time for proper averaging
            if "moving_time" not in activities_df.columns:
                continue

            total_time = activities_df["moving_time"].sum()
            if total_time == 0:
                continue

            # Calculate weighted averages
            for col in cols:
                zone_name = col.split("_")[-2]  # Extract z1, z2, or z3
                weighted_sum = (activities_df[col] * activities_df["moving_time"]).sum()
                weekly_avg = weighted_sum / total_time
                weekly_metrics[f"weekly_{metric_type}_tid_{zone_name}_percentage"] = (
                    weekly_avg
                )

            # Calculate weekly polarization metrics
            z1_col, z2_col, z3_col = cols
            z1_weighted = (
                activities_df[z1_col] * activities_df["moving_time"]
            ).sum() / total_time
            z2_weighted = (
                activities_df[z2_col] * activities_df["moving_time"]
            ).sum() / total_time
            z3_weighted = (
                activities_df[z3_col] * activities_df["moving_time"]
            ).sum() / total_time

            if z2_weighted > 0:
                weekly_metrics[f"weekly_{metric_type}_polarization_index"] = (
                    z1_weighted + z3_weighted
                ) / z2_weighted

            if z3_weighted > 0:
                weekly_metrics[f"weekly_{metric_type}_tdr"] = z1_weighted / z3_weighted

        return weekly_metrics
