"""
High-level metric calculator orchestrators.

This module provides the main calculator class that coordinates
all specialized metric calculators.

NOTE: Data is pre-split into raw/moving DataFrames upstream. Calculators receive
a single DataFrame and return unprefixed metric names. The orchestrator should
be called once per mode (raw, moving) with the appropriate DataFrame.
"""

import logging

import numpy as np
import pandas as pd

from ..settings import Settings
from .advanced_power import AdvancedPowerCalculator
from .basic import BasicMetricsCalculator
from .climbing import ClimbingCalculator
from .efficiency import EfficiencyCalculator
from .fatigue import FatigueCalculator
from .heartrate import HeartRateCalculator
from .pace import PaceCalculator
from .power import PowerCalculator
from .power_curve import interval_name_from_seconds
from .tid import TIDCalculator
from .zones import ZoneCalculator

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Orchestrates calculation of all metrics.

    This class coordinates multiple specialized calculators to compute
    comprehensive metrics from activity stream data. Data is expected to
    be pre-split into raw or moving DataFrames upstream.
    """

    def __init__(self, settings: Settings):
        """
        Initialize calculator with all sub-calculators.

        Args:
            settings: Application settings containing thresholds and configuration
        """
        self.settings = settings
        self.power_calculator = PowerCalculator(settings)
        self.advanced_power_calculator = AdvancedPowerCalculator(settings)
        self.climbing_calculator = ClimbingCalculator(settings)
        self.hr_calculator = HeartRateCalculator(settings)
        self.efficiency_calculator = EfficiencyCalculator(settings)
        self.pace_calculator = PaceCalculator(settings)
        self.zone_calculator = ZoneCalculator(settings)
        self.tid_calculator = TIDCalculator(settings)
        self.fatigue_calculator = FatigueCalculator(settings)
        self.basic_calculator = BasicMetricsCalculator(settings)

    def compute_all_metrics(
        self,
        stream_df: pd.DataFrame,
        activity_type: str,
        include_power_curve: bool = False,
    ) -> dict[str, float | str]:
        """
        Compute all metrics for a single pre-split DataFrame.

        NOTE: This method should be called once per mode (raw, moving) with
        the appropriate pre-split DataFrame. Metrics are returned without prefixes.

        Args:
            stream_df: Pre-split DataFrame containing activity stream data
            activity_type: Type of activity ('ride', 'run', etc.)
            include_power_curve: Whether to compute power curve metrics (typically
                                only for raw data)

        Returns:
            Dictionary containing all calculated metrics (no prefixes)
        """
        all_metrics: dict[str, float | str] = {}

        # Determine which calculators to use based on activity type
        is_cycling = activity_type.lower() in ["ride", "virtualride", "virtual_ride"]
        is_running = activity_type.lower() == "run"

        try:
            # Power metrics (cycling)
            if is_cycling:
                power_metrics = self.power_calculator.calculate(stream_df)
                all_metrics.update(power_metrics)

                # Advanced power metrics (W' balance, time in zones, etc.)
                advanced_power_metrics = self.advanced_power_calculator.calculate(
                    stream_df
                )
                all_metrics.update(advanced_power_metrics)

                # Climbing metrics (VAM, climbing power)
                climbing_metrics = self.climbing_calculator.calculate(stream_df)
                all_metrics.update(climbing_metrics)

                # Power curve (MMP) metrics - only if requested
                if include_power_curve:
                    power_curve_metrics = self._calculate_power_curve_metrics(stream_df)
                    all_metrics.update(power_curve_metrics)

            # Heart rate metrics (all activities)
            hr_metrics = self.hr_calculator.calculate(stream_df)
            all_metrics.update(hr_metrics)

            # Efficiency metrics (cycling and running)
            efficiency_metrics = self.efficiency_calculator.calculate(stream_df)
            all_metrics.update(efficiency_metrics)

            # Pace metrics (running)
            if is_running:
                pace_metrics = self.pace_calculator.calculate(stream_df)
                all_metrics.update(pace_metrics)

            # Basic metrics (cadence, speed)
            basic_metrics = self.basic_calculator.calculate(stream_df)
            all_metrics.update(basic_metrics)

            # Zone distributions
            zone_metrics = self.zone_calculator.calculate(stream_df)
            all_metrics.update(zone_metrics)

            # Training Intensity Distribution
            tid_metrics = self.tid_calculator.calculate(stream_df)
            all_metrics.update(tid_metrics)

            # Add TID classification based on computed TID metrics
            tid_classification = self._calculate_tid_classification(tid_metrics)
            all_metrics.update(tid_classification)

            # Fatigue resistance (only for activities > 1 hour)
            fatigue_metrics = self.fatigue_calculator.calculate(stream_df)
            all_metrics.update(fatigue_metrics)

            # Interval fatigue analysis (5-minute intervals)
            if is_cycling and include_power_curve:
                interval_fatigue = self.fatigue_calculator.calculate_interval_fatigue(
                    stream_df, interval_duration=300
                )
                all_metrics.update(interval_fatigue)

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")

        # Add basic temporal metrics
        all_metrics.update(self._calculate_basic_metrics(stream_df))

        return all_metrics

    def _calculate_basic_metrics(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate basic temporal and distance metrics.

        Args:
            stream_df: DataFrame containing activity stream data

        Returns:
            Dictionary of basic metrics
        """
        metrics = {}

        try:
            # Time metrics
            if "time" in stream_df.columns:
                metrics["total_time"] = float(
                    stream_df["time"].iloc[-1] - stream_df["time"].iloc[0]
                )
            else:
                metrics["total_time"] = 0.0

            if "moving" in stream_df.columns:
                metrics["moving_time"] = float(stream_df["moving"].sum())
            else:
                metrics["moving_time"] = 0.0

            # Distance
            if "distance" in stream_df.columns:
                metrics["distance"] = float(stream_df["distance"].iloc[-1])
            else:
                metrics["distance"] = 0.0

            # Elevation
            if "altitude" in stream_df.columns:
                diffs = stream_df["altitude"].diff()
                metrics["elevation_gain"] = (
                    float(diffs[diffs > 0].sum()) if not diffs.empty else 0.0
                )
            else:
                metrics["elevation_gain"] = 0.0

        except Exception as e:
            logger.warning(f"Error calculating basic metrics: {e}")
            metrics.setdefault("total_time", 0.0)
            metrics.setdefault("moving_time", 0.0)
            metrics.setdefault("distance", 0.0)
            metrics.setdefault("elevation_gain", 0.0)

        return metrics

    def _calculate_power_curve_metrics(
        self, stream_df: pd.DataFrame
    ) -> dict[str, float]:
        """
        Calculate power curve (MMP) metrics for various durations.

        Args:
            stream_df: DataFrame containing activity stream data

        Returns:
            Dictionary of power curve metrics
        """
        metrics: dict[str, float] = {}

        if "watts" not in stream_df.columns:
            return metrics

        try:
            active_watts = stream_df["watts"][stream_df["watts"] > 0]
            if active_watts.empty:
                return metrics

            # Calculate MMP for each configured interval
            for _interval_name, duration in self.settings.power_curve_intervals.items():
                duration = int(duration)
                if duration <= 0 or len(active_watts) < duration:
                    continue

                max_avg = (
                    active_watts.rolling(window=duration, min_periods=duration)
                    .mean()
                    .max()
                )

                if np.isfinite(max_avg):
                    # Use interval_name_from_seconds for consistent naming
                    col_name = f"power_curve_{interval_name_from_seconds(duration)}"
                    metrics[col_name] = float(max_avg)

        except Exception as e:
            logger.warning(f"Error calculating power curve metrics: {e}")

        return metrics

    def _calculate_tid_classification(
        self, tid_metrics: dict[str, float]
    ) -> dict[str, float | str]:
        """
        Calculate TID classification based on computed TID metrics.

        Args:
            tid_metrics: Dictionary of TID metrics from TIDCalculator (no prefixes)

        Returns:
            Dictionary with TID classification (no prefixes)
        """
        metrics: dict[str, float | str] = {}

        # Try power-based classification first
        power_z1_key = "power_tid_z1_percentage"
        power_z2_key = "power_tid_z2_percentage"
        power_z3_key = "power_tid_z3_percentage"

        if all(k in tid_metrics for k in [power_z1_key, power_z2_key, power_z3_key]):
            classification = self.tid_calculator.calculate_tid_classification(
                tid_metrics[power_z1_key],
                tid_metrics[power_z2_key],
                tid_metrics[power_z3_key],
            )
            metrics["power_tid_classification"] = classification

        # Also try HR-based classification
        hr_z1_key = "hr_tid_z1_percentage"
        hr_z2_key = "hr_tid_z2_percentage"
        hr_z3_key = "hr_tid_z3_percentage"

        if all(k in tid_metrics for k in [hr_z1_key, hr_z2_key, hr_z3_key]):
            classification = self.tid_calculator.calculate_tid_classification(
                tid_metrics[hr_z1_key],
                tid_metrics[hr_z2_key],
                tid_metrics[hr_z3_key],
            )
            metrics["hr_tid_classification"] = classification

        return metrics
