"""
Zone distribution calculations.

This module handles time-in-zone calculations for:
- Power zones (7-zone Coggan model)
- Heart rate zones (5-zone model)
- Cadence zones

Also provides utility functions for binning features and calculating power profiles.
"""

import logging

import numpy as np
import pandas as pd
from pandas import Series

from ..constants import HeartRateZoneThresholds, PowerZoneThresholds
from ..exceptions import MetricCalculationError, ValidationError
from ..models import MaximumMeanPowers, PowerProfile
from ..settings import Settings
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class ZoneCalculator(BaseMetricCalculator):
    """Calculates zone distributions from activity stream data."""

    def calculate(
        self, stream_df: pd.DataFrame, moving_only: bool = False
    ) -> dict[str, float]:
        """
        Calculate zone distributions.

        Args:
            stream_df: DataFrame containing activity stream data
            moving_only: If True, only use data where moving=True

        Returns:
            Dictionary of zone metrics with appropriate prefix
        """
        df = self._filter_moving(stream_df, moving_only)
        prefix = self._get_prefix(moving_only)
        metrics = {}

        # Calculate power zones if available
        if "watts" in df.columns and self.settings.ftp > 0:
            power_zones = self._calculate_power_zones(df["watts"])
            for zone_name, percentage in power_zones.items():
                metrics[f"{prefix}{zone_name}_percentage"] = percentage

        # Calculate HR zones if available
        if "heartrate" in df.columns and self.settings.fthr > 0:
            hr_zones = self._calculate_hr_zones(df["heartrate"])
            for zone_name, percentage in hr_zones.items():
                metrics[f"{prefix}{zone_name}_percentage"] = percentage

        return metrics

    def _calculate_power_zones(self, power_series: pd.Series) -> dict[str, float]:
        """Calculate power zone distribution (Coggan 7-zone model)."""
        ftp = self.settings.ftp
        total_points = len(power_series)

        if total_points == 0:
            return {}

        zones = {
            "power_z1": (0, PowerZoneThresholds.ZONE_1_MAX * ftp),
            "power_z2": (
                PowerZoneThresholds.ZONE_1_MAX * ftp,
                PowerZoneThresholds.ZONE_2_MAX * ftp,
            ),
            "power_z3": (
                PowerZoneThresholds.ZONE_2_MAX * ftp,
                PowerZoneThresholds.ZONE_3_MAX * ftp,
            ),
            "power_z4": (
                PowerZoneThresholds.ZONE_3_MAX * ftp,
                PowerZoneThresholds.ZONE_4_MAX * ftp,
            ),
            "power_z5": (
                PowerZoneThresholds.ZONE_4_MAX * ftp,
                PowerZoneThresholds.ZONE_5_MAX * ftp,
            ),
            "power_z6": (
                PowerZoneThresholds.ZONE_5_MAX * ftp,
                PowerZoneThresholds.ZONE_6_MAX * ftp,
            ),
            "power_z7": (PowerZoneThresholds.ZONE_6_MAX * ftp, float("inf")),
        }

        zone_percentages = {}
        for zone_name, (lower, upper) in zones.items():
            mask = (power_series >= lower) & (power_series < upper)
            time_in_zone = mask.sum()
            zone_percentages[zone_name] = (time_in_zone / total_points) * 100

        return zone_percentages

    def _calculate_hr_zones(self, hr_series: pd.Series) -> dict[str, float]:
        """Calculate HR zone distribution (5-zone model)."""
        fthr = self.settings.fthr
        total_points = len(hr_series)

        if total_points == 0:
            return {}

        zones = {
            "hr_z1": (0, HeartRateZoneThresholds.ZONE_1_MAX * fthr),
            "hr_z2": (
                HeartRateZoneThresholds.ZONE_1_MAX * fthr,
                HeartRateZoneThresholds.ZONE_2_MAX * fthr,
            ),
            "hr_z3": (
                HeartRateZoneThresholds.ZONE_2_MAX * fthr,
                HeartRateZoneThresholds.ZONE_3_MAX * fthr,
            ),
            "hr_z4": (
                HeartRateZoneThresholds.ZONE_3_MAX * fthr,
                HeartRateZoneThresholds.ZONE_4_MAX * fthr,
            ),
            "hr_z5": (HeartRateZoneThresholds.ZONE_4_MAX * fthr, float("inf")),
        }

        zone_percentages = {}
        for zone_name, (lower, upper) in zones.items():
            mask = (hr_series >= lower) & (hr_series < upper)
            time_in_zone = mask.sum()
            zone_percentages[zone_name] = (time_in_zone / total_points) * 100

        return zone_percentages

    @staticmethod
    def bin_feature(
        feature: Series,
        bins_dict: dict[str, tuple[float, float]],
        exclude_coasting: bool = False,
        threshold: float | None = None,
    ) -> dict[str, float]:
        """
        Calculate the percentage of time spent in each bin for a given feature.

        Args:
            feature: Series containing feature data
            bins_dict: Dictionary of zone boundaries
            exclude_coasting: Whether to exclude coasting (low power) data
            threshold: Value to use for coasting exclusion (e.g., FTP for power)

        Returns:
            Dictionary mapping zone names to percentage time spent in each zone

        Raises:
            ValidationError: If inputs are invalid
            MetricCalculationError: If calculations fail
        """
        try:
            if feature.empty:
                return dict.fromkeys(bins_dict.keys(), 0.0)

            processed_feature = feature.copy()

            if (
                exclude_coasting
                and threshold is not None
                and "watts" in str(feature.name).lower()
            ):
                coasting_threshold = threshold * 0.50
                processed_feature = processed_feature[
                    processed_feature > coasting_threshold
                ]
                if processed_feature.empty:
                    return dict.fromkeys(bins_dict.keys(), 0.0)

            # Create bin edges and labels
            bins_edges: list[float] = []
            zone_labels: list[str] = []

            sorted_zones = sorted(bins_dict.items(), key=lambda x: x[1][0])

            for zone_name, (lower, _) in sorted_zones:
                bins_edges.append(lower)
                zone_labels.append(zone_name)

            bins_edges.append(sorted_zones[-1][1][1])

            if len(bins_edges) > 8:
                raise ValidationError("Too many zones defined: maximum is 7.")

            total_points = len(processed_feature)
            if total_points == 0:
                return dict.fromkeys(bins_dict.keys(), 0.0)

            binned = pd.cut(
                processed_feature,
                bins=bins_edges,
                labels=zone_labels,
                include_lowest=True,
                right=True,
            )

            zone_counts = binned.value_counts()
            return {
                str(zone): float((count / total_points) * 100)
                for zone, count in zone_counts.items()
            }

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise MetricCalculationError(f"Error binning feature data: {str(e)}") from e

    @staticmethod
    def calculate_power_profile(
        stream_df: pd.DataFrame, settings: Settings
    ) -> PowerProfile:
        """
        Calculate power profile metrics including MMP curve.

        Args:
            stream_df: DataFrame containing activity stream data
            settings: Application settings

        Returns:
            PowerProfile object with calculated metrics

        Raises:
            ValidationError: If inputs are invalid
            MetricCalculationError: If calculations fail
        """
        try:
            if stream_df.empty:
                raise ValidationError("Stream data is empty")
            if "watts" not in stream_df.columns:
                raise ValidationError("Power data not found in stream data")

            active_watts = stream_df["watts"][stream_df["watts"] > 0]
            if active_watts.empty:
                return PowerProfile(
                    mmp_curve=MaximumMeanPowers(durations=[], powers=[]),
                    cp_model=None,
                    time_to_exhaustion=None,
                    aei=None,
                )

            # Calculate MMP curve
            durations = []
            powers = []
            for duration in settings.power_curve_intervals.values():
                duration = int(duration)
                if duration <= 0:
                    continue
                if len(active_watts) >= duration:
                    max_avg = float(
                        active_watts.rolling(window=duration, min_periods=duration)
                        .mean()
                        .max()
                    )
                    if np.isfinite(max_avg):
                        durations.append(duration)
                        powers.append(max_avg)

            mmp_curve = MaximumMeanPowers(durations=durations, powers=powers)
            return PowerProfile(
                mmp_curve=mmp_curve,
                cp_model=None,
                time_to_exhaustion=None,
                aei=None,
            )

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise MetricCalculationError(
                f"Error calculating power profile: {str(e)}"
            ) from e
