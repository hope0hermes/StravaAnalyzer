"""
High-level metric calculator orchestrators.

This module provides the main calculator class that coordinates
all specialized metric calculators.
"""

import logging

import pandas as pd

from ..settings import Settings
from .efficiency import EfficiencyCalculator
from .fatigue import FatigueCalculator
from .heartrate import HeartRateCalculator
from .pace import PaceCalculator
from .power import PowerCalculator
from .tid import TIDCalculator
from .zones import ZoneCalculator

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Orchestrates calculation of all metrics.

    This class coordinates multiple specialized calculators to compute
    comprehensive metrics from activity stream data.
    """

    def __init__(self, settings: Settings):
        """
        Initialize calculator with all sub-calculators.

        Args:
            settings: Application settings containing thresholds and configuration
        """
        self.settings = settings
        self.power_calculator = PowerCalculator(settings)
        self.hr_calculator = HeartRateCalculator(settings)
        self.efficiency_calculator = EfficiencyCalculator(settings)
        self.pace_calculator = PaceCalculator(settings)
        self.zone_calculator = ZoneCalculator(settings)
        self.tid_calculator = TIDCalculator(settings)
        self.fatigue_calculator = FatigueCalculator(settings)

    def compute_all_metrics(
        self,
        stream_df: pd.DataFrame,
        activity_type: str,
        compute_raw: bool = True,
        compute_moving: bool = True,
    ) -> dict[str, float]:
        """
        Compute all metrics for both raw and moving-only data.

        Args:
            stream_df: DataFrame containing activity stream data
            activity_type: Type of activity ('ride', 'run', etc.)
            compute_raw: Whether to compute metrics from all data
            compute_moving: Whether to compute metrics from moving-only data

        Returns:
            Dictionary containing all calculated metrics with appropriate prefixes
        """
        all_metrics = {}

        # Determine which calculators to use based on activity type
        is_cycling = activity_type.lower() in ["ride", "virtualride", "virtual_ride"]
        is_running = activity_type.lower() == "run"

        # Compute for raw and/or moving data
        for moving_only in [False, True]:
            if (moving_only and not compute_moving) or (
                not moving_only and not compute_raw
            ):
                continue

            try:
                # Power metrics (cycling)
                if is_cycling:
                    power_metrics = self.power_calculator.calculate(
                        stream_df, moving_only
                    )
                    all_metrics.update(power_metrics)

                # Heart rate metrics (all activities)
                hr_metrics = self.hr_calculator.calculate(stream_df, moving_only)
                all_metrics.update(hr_metrics)

                # Efficiency metrics (cycling and running)
                efficiency_metrics = self.efficiency_calculator.calculate(
                    stream_df, moving_only
                )
                all_metrics.update(efficiency_metrics)

                # Pace metrics (running)
                if is_running:
                    pace_metrics = self.pace_calculator.calculate(
                        stream_df, moving_only
                    )
                    all_metrics.update(pace_metrics)

                # Zone distributions
                zone_metrics = self.zone_calculator.calculate(stream_df, moving_only)
                all_metrics.update(zone_metrics)

                # Training Intensity Distribution
                tid_metrics = self.tid_calculator.calculate(stream_df, moving_only)
                all_metrics.update(tid_metrics)

                # Fatigue resistance (only for activities > 1 hour)
                fatigue_metrics = self.fatigue_calculator.calculate(
                    stream_df, moving_only
                )
                all_metrics.update(fatigue_metrics)

            except Exception as e:
                prefix = "moving_" if moving_only else "raw_"
                logger.error(f"Error calculating {prefix}metrics: {e}")

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
