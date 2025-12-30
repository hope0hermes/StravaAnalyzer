"""
Advanced power metrics calculations.

This module handles advanced power-based metrics including:
- W' (W prime) balance tracking
- Match burn counting
- Time above various power thresholds
- Negative split analysis
- Cardiac drift
"""

import logging

import numpy as np
import pandas as pd

from ..constants import TimeConstants
from .base import BaseMetricCalculator

logger = logging.getLogger(__name__)


class AdvancedPowerCalculator(BaseMetricCalculator):
    """Calculates advanced power-based metrics from activity stream data."""

    def calculate(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate all advanced power metrics.

        Args:
            stream_df: DataFrame containing activity stream data (pre-split)

        Returns:
            Dictionary of advanced power metrics (no prefix)
        """
        metrics: dict[str, float] = {}

        if "watts" not in stream_df.columns:
            return self._get_empty_metrics()

        try:
            # Time above various FTP percentages
            time_above_90 = self._calculate_time_above_threshold(stream_df, 0.90)
            time_sweet_spot = self._calculate_time_in_range(stream_df, 0.88, 0.94)

            metrics["time_above_90_ftp"] = time_above_90
            metrics["time_sweet_spot"] = time_sweet_spot

            # W' balance metrics (if CP model available)
            if hasattr(self.settings, "cp") and hasattr(self.settings, "w_prime"):
                w_prime_metrics = self._calculate_w_prime_balance(stream_df)
                metrics.update(w_prime_metrics)
            else:
                metrics["w_prime_balance_min"] = 0.0
                metrics["match_burn_count"] = 0.0

            # Negative split analysis
            negative_split = self._calculate_negative_split_index(stream_df)
            metrics["negative_split_index"] = negative_split

            # Cardiac drift (requires HR data)
            if "heartrate" in stream_df.columns:
                cardiac_drift = self._calculate_cardiac_drift(stream_df)
                metrics["cardiac_drift"] = cardiac_drift
            else:
                metrics["cardiac_drift"] = 0.0

            # Estimated FTP from this ride
            estimated_ftp = self._estimate_ftp_from_ride(stream_df)
            metrics["estimated_ftp"] = estimated_ftp

            return metrics

        except Exception as e:
            logger.warning(f"Error calculating advanced power metrics: {e}")
            return self._get_empty_metrics()

    def _calculate_time_above_threshold(
        self, stream_df: pd.DataFrame, threshold_pct: float
    ) -> float:
        """
        Calculate time spent above a power threshold (as % of FTP).

        Args:
            stream_df: DataFrame with watts column
            threshold_pct: Threshold as decimal (e.g., 0.90 for 90% FTP)

        Returns:
            Time in seconds above threshold
        """
        if self.settings.ftp == 0:
            return 0.0

        threshold_watts = self.settings.ftp * threshold_pct
        above_threshold = stream_df["watts"] > threshold_watts

        return float(above_threshold.sum())

    def _calculate_time_in_range(
        self, stream_df: pd.DataFrame, lower_pct: float, upper_pct: float
    ) -> float:
        """
        Calculate time spent in a power range (as % of FTP).

        Args:
            stream_df: DataFrame with watts column
            lower_pct: Lower threshold as decimal (e.g., 0.88)
            upper_pct: Upper threshold as decimal (e.g., 0.94)

        Returns:
            Time in seconds in range
        """
        if self.settings.ftp == 0:
            return 0.0

        lower_watts = self.settings.ftp * lower_pct
        upper_watts = self.settings.ftp * upper_pct

        in_range = (stream_df["watts"] >= lower_watts) & (
            stream_df["watts"] <= upper_watts
        )

        return float(in_range.sum())

    def _calculate_w_prime_balance(self, stream_df: pd.DataFrame) -> dict[str, float]:
        """
        Calculate W' balance throughout the ride and count match burns.

        W' balance tracks anaerobic capacity depletion and recovery.
        Match burn = significant W' expenditure (>50% of total W').

        Args:
            stream_df: DataFrame with watts column

        Returns:
            Dictionary with w_prime_balance_min and match_burn_count
        """
        metrics = {"w_prime_balance_min": 0.0, "match_burn_count": 0}

        if not hasattr(self.settings, "cp") or not hasattr(self.settings, "w_prime"):
            return metrics

        cp = self.settings.cp
        w_prime = self.settings.w_prime

        if cp == 0 or w_prime == 0:
            return metrics

        # Initialize W' balance
        w_balance = np.zeros(len(stream_df))
        w_balance[0] = w_prime

        power = stream_df["watts"].values

        # Calculate W' balance second-by-second
        for i in range(1, len(power)):
            if power[i] > cp:
                # Above CP: deplete W'
                w_expended = power[i] - cp
                w_balance[i] = w_balance[i - 1] - w_expended
            else:
                # Below CP: recover W' (simplified exponential recovery)
                recovery_rate = (cp - power[i]) / cp
                tau = 546 * np.exp(-0.01 * (cp - power[i])) + 316  # Skiba model
                w_recovered = (w_prime - w_balance[i - 1]) * (1 - np.exp(-1 / tau))
                w_balance[i] = w_balance[i - 1] + w_recovered

            # Clamp to valid range
            w_balance[i] = np.clip(w_balance[i], 0, w_prime)

        # Find minimum W' balance
        min_w_balance = float(np.min(w_balance))
        metrics["w_prime_balance_min"] = min_w_balance

        # Count match burns (drops > 50% of W')
        w_pct_balance = w_balance / w_prime
        match_threshold = 0.50

        # Find local minima where W' dropped significantly
        match_count = 0
        in_match = False

        for i in range(1, len(w_pct_balance)):
            if w_pct_balance[i] < match_threshold and not in_match:
                match_count += 1
                in_match = True
            elif w_pct_balance[i] > match_threshold + 0.1:  # Hysteresis
                in_match = False

        metrics["match_burn_count"] = float(match_count)

        return metrics

    def _calculate_negative_split_index(self, stream_df: pd.DataFrame) -> float:
        """
        Calculate negative split index (NP 2nd half / NP 1st half).

        < 1.0 = negative split (stronger finish)
        = 1.0 = even pacing
        > 1.0 = positive split (faded)

        Args:
            stream_df: DataFrame with watts column

        Returns:
            Negative split index ratio
        """
        if len(stream_df) < 60:  # Need at least 1 minute of data
            return 1.0

        midpoint = len(stream_df) // 2

        first_half = stream_df.iloc[:midpoint]
        second_half = stream_df.iloc[midpoint:]

        # Calculate NP for each half (simplified 30-sec rolling avg)
        np_first = self._calculate_normalized_power_simple(first_half["watts"])
        np_second = self._calculate_normalized_power_simple(second_half["watts"])

        if np_first == 0:
            return 1.0

        return float(np_second / np_first)

    def _calculate_normalized_power_simple(self, power_series: pd.Series) -> float:
        """Simplified NP calculation for halves."""
        if power_series.empty:
            return 0.0

        # 30-second rolling average
        rolling_avg = power_series.rolling(window=30, center=True).mean()

        # Raise to 4th power, take mean, then 4th root
        np_value = np.power(np.power(rolling_avg.dropna(), 4).mean(), 0.25)

        return float(np_value) if not np.isnan(np_value) else 0.0

    def _calculate_cardiac_drift(self, stream_df: pd.DataFrame) -> float:
        """
        Calculate cardiac drift (EF 1st half vs 2nd half).

        Cardiac drift % = (EF_second - EF_first) / EF_first × 100

        Negative drift = fatigue/dehydration (EF decreasing)
        Positive drift = warm-up effect (EF improving - rare)

        Consistent with power_hr_decoupling formula.

        Args:
            stream_df: DataFrame with watts and heartrate columns

        Returns:
            Cardiac drift percentage
        """
        if (
            "watts" not in stream_df.columns
            or "heartrate" not in stream_df.columns
            or len(stream_df) < 600  # Need at least 10 min
        ):
            return 0.0

        midpoint = len(stream_df) // 2

        first_half = stream_df.iloc[:midpoint]
        second_half = stream_df.iloc[midpoint:]

        # Calculate EF for each half (NP / Avg HR)
        ef_first = self._calculate_ef_simple(first_half)
        ef_second = self._calculate_ef_simple(second_half)

        if ef_first == 0:
            return 0.0

        drift_pct = ((ef_second - ef_first) / ef_first) * 100

        return float(drift_pct)

    def _calculate_ef_simple(self, df: pd.DataFrame) -> float:
        """Calculate simple EF for a segment."""
        if df.empty:
            return 0.0

        np_simple = self._calculate_normalized_power_simple(df["watts"])
        avg_hr = df["heartrate"].mean()

        if avg_hr == 0:
            return 0.0

        return np_simple / avg_hr

    def _estimate_ftp_from_ride(self, stream_df: pd.DataFrame) -> float:
        """
        Estimate FTP from this ride using best 20-minute power.

        FTP ≈ 95% of best 20-minute average power

        Args:
            stream_df: DataFrame with watts column

        Returns:
            Estimated FTP in watts
        """
        if len(stream_df) < 1200:  # Need at least 20 minutes
            return 0.0

        window_size = 1200  # 20 minutes in seconds
        power = stream_df["watts"].values

        # Calculate 20-minute rolling average
        rolling_avg = pd.Series(power).rolling(window=window_size).mean()

        if rolling_avg.empty:
            return 0.0

        best_20min = rolling_avg.max()

        if np.isnan(best_20min) or best_20min == 0:
            return 0.0

        # FTP is ~95% of 20-minute power
        estimated_ftp = best_20min * 0.95

        return float(estimated_ftp)

    def _get_empty_metrics(self) -> dict[str, float]:
        """Return empty metrics dict with default values."""
        return {
            "time_above_90_ftp": 0.0,
            "time_sweet_spot": 0.0,
            "w_prime_balance_min": 0.0,
            "match_burn_count": 0.0,
            "negative_split_index": 1.0,
            "cardiac_drift": 0.0,
            "estimated_ftp": 0.0,
        }
