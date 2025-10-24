"""
Training Intensity Distribution (TID) analysis.

This module provides comprehensive TID metrics including:
- Time-in-zone distributions
- Polarization analysis
- TID ratios for various zone models
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

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate TID metrics.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of TID metrics with appropriate prefix
        """
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)
        metrics = {}

        # Calculate TID metrics based on available data
        if "watts" in df.columns and self.settings.ftp > 0:
            power_tid = self._calculate_power_tid(df["watts"])
            for key, value in power_tid.items():
                metrics[f"{prefix}{key}"] = value

        if "heartrate" in df.columns and self.settings.fthr > 0:
            hr_tid = self._calculate_hr_tid(df["heartrate"])
            for key, value in hr_tid.items():
                metrics[f"{prefix}{key}"] = value

        return metrics

    def _calculate_power_tid(self, power_series: pd.Series) -> dict[str, float]:
        """
        Calculate TID metrics based on power zones.

        Uses 3-zone model:
        - Zone 1 (Low): < 76% FTP (combines Z1 + Z2)
        - Zone 2 (Moderate): 76-90% FTP (Z3)
        - Zone 3 (High): > 90% FTP (combines Z4-Z7)

        Args:
            power_series: Power data

        Returns:
            Dictionary of TID metrics
        """
        if power_series.empty:
            return {}

        ftp = self.settings.ftp
        total_points = len(power_series)

        # 3-zone TID model
        zone1_threshold = 0.76 * ftp  # Low intensity
        zone2_threshold = 0.90 * ftp  # Moderate intensity

        zone1_time = (power_series < zone1_threshold).sum()
        zone2_time = (
            (power_series >= zone1_threshold) & (power_series < zone2_threshold)
        ).sum()
        zone3_time = (power_series >= zone2_threshold).sum()

        # Calculate percentages
        z1_pct = (zone1_time / total_points) * 100
        z2_pct = (zone2_time / total_points) * 100
        z3_pct = (zone3_time / total_points) * 100

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

    def _calculate_hr_tid(self, hr_series: pd.Series) -> dict[str, float]:
        """
        Calculate TID metrics based on heart rate zones.

        Uses 3-zone model:
        - Zone 1 (Low): < 82% FTHR (Z1)
        - Zone 2 (Moderate): 82-94% FTHR (Z2 + Z3)
        - Zone 3 (High): > 94% FTHR (Z4 + Z5)

        Args:
            hr_series: Heart rate data

        Returns:
            Dictionary of TID metrics
        """
        if hr_series.empty:
            return {}

        fthr = self.settings.fthr
        total_points = len(hr_series)

        # 3-zone TID model based on HR
        zone1_threshold = HeartRateZoneThresholds.ZONE_1_MAX * fthr  # 82% FTHR
        zone2_threshold = HeartRateZoneThresholds.ZONE_3_MAX * fthr  # 94% FTHR

        zone1_time = (hr_series < zone1_threshold).sum()
        zone2_time = (
            (hr_series >= zone1_threshold) & (hr_series < zone2_threshold)
        ).sum()
        zone3_time = (hr_series >= zone2_threshold).sum()

        # Calculate percentages
        z1_pct = (zone1_time / total_points) * 100
        z2_pct = (zone2_time / total_points) * 100
        z3_pct = (zone3_time / total_points) * 100

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

    def calculate_weekly_tid(
        self, activities_df: pd.DataFrame, metric_prefix: str = "raw_"
    ) -> dict[str, float]:
        """
        Calculate weekly TID from multiple activities.

        Args:
            activities_df: DataFrame with activity metrics
            metric_prefix: Prefix for metrics (raw_ or moving_)

        Returns:
            Weekly aggregated TID metrics
        """
        tid_cols = {
            "power": [
                f"{metric_prefix}power_tid_z1_percentage",
                f"{metric_prefix}power_tid_z2_percentage",
                f"{metric_prefix}power_tid_z3_percentage",
            ],
            "hr": [
                f"{metric_prefix}hr_tid_z1_percentage",
                f"{metric_prefix}hr_tid_z2_percentage",
                f"{metric_prefix}hr_tid_z3_percentage",
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
