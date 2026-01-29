"""
Zone distribution calculations.

This module handles time-in-zone calculations for:
- Power zones (7-zone model from settings, LT-based or Coggan percentage-based)
- Heart rate zones (5-zone model from settings, LT-based or percentage-based)
- Cadence zones

Also provides utility functions for binning features and calculating power profiles.

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names.
"""

import logging

import numpy as np
import pandas as pd
from pandas import Series

from ..exceptions import MetricCalculationError, ValidationError
from ..models import MaximumMeanPowers, PowerProfile
from ..settings import Settings
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class ZoneCalculator(BaseMetricCalculator):
    """Calculates zone distributions from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate zone distributions using time-weighted calculations.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of zone metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        # Calculate power zones if available
        if "watts" in stream_df.columns and self.settings.ftp > 0:
            power_zones = self._calculate_power_zones(stream_df["watts"], stream_df)
            for zone_name, percentage in power_zones.items():
                metrics[f"{zone_name}_percentage"] = percentage

        # Calculate HR zones if available
        if "heartrate" in stream_df.columns and self.settings.fthr > 0:
            hr_zones = self._calculate_hr_zones(stream_df["heartrate"], stream_df)
            for zone_name, percentage in hr_zones.items():
                metrics[f"{zone_name}_percentage"] = percentage

        return metrics

    def _calculate_power_zones(
        self, power_series: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """Calculate power zone distribution using time-weighted calculations.

        Uses the power zones defined in settings, which can be:
        - LT-based 7-zone model (if lt1_power and lt2_power are configured)
        - Coggan percentage-based 7-zone model (fallback)

        Time-weighted calculation ensures accurate percentages regardless of
        variable sampling rates or gaps in the data.
        """
        if power_series.empty:
            return {}

        # Get time deltas for time-weighted calculation
        time_deltas = self._calculate_time_deltas(stream_df)
        total_time = time_deltas.sum()

        if total_time == 0:
            return {}

        # Use zones from settings (LT-based or percentage-based)
        zones = self.settings.power_zones

        zone_percentages = {}
        for zone_name, (lower, upper) in zones.items():
            # Convert zone name from settings format (power_zone_1) to output format (power_z1)
            output_name = zone_name.replace("power_zone_", "power_z")
            mask = (power_series >= lower) & (power_series < upper)
            # Time-weighted: sum of time deltas where condition is true
            time_in_zone = time_deltas[mask].sum()
            zone_percentages[output_name] = (time_in_zone / total_time) * 100

        return zone_percentages

    def _calculate_hr_zones(
        self, hr_series: pd.Series, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """Calculate HR zone distribution using time-weighted calculations.

        Uses the HR zones defined in settings, which can be:
        - LT-based 5-zone model (if lt1_hr and lt2_hr are configured)
        - Percentage-based 5-zone model (fallback)

        Time-weighted calculation ensures accurate percentages regardless of
        variable sampling rates or gaps in the data.
        """
        if hr_series.empty:
            return {}

        # Get time deltas for time-weighted calculation
        time_deltas = self._calculate_time_deltas(stream_df)
        total_time = time_deltas.sum()

        if total_time == 0:
            return {}

        # Use zones from settings (LT-based or percentage-based)
        zones = self.settings.hr_zone_ranges

        zone_percentages = {}
        for zone_name, (lower, upper) in zones.items():
            # Convert zone name from settings format (hr_zone_1) to output format (hr_z1)
            output_name = zone_name.replace("hr_zone_", "hr_z")
            mask = (hr_series >= lower) & (hr_series < upper)
            # Time-weighted: sum of time deltas where condition is true
            time_in_zone = time_deltas[mask].sum()
            zone_percentages[output_name] = (time_in_zone / total_time) * 100

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
