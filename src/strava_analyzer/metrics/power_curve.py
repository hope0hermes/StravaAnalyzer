"""
Power curve analysis and critical power modeling.

This module provides functions for analyzing power-duration curves,
including Critical Power (CP) and W' (W prime) estimation.
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


# pylint: disable=C0103  # Allow short variable names for mathematical functions.
def hyperbolic_model(
    t: np.ndarray | float, CP: float, W_prime: float
) -> np.ndarray | float:
    """
    Hyperbolic power-duration model: P(t) = CP + W' / t.

    Args:
        t: Duration in seconds
        CP: Critical Power
        W_prime: Anaerobic Work Capacity

    Returns:
        Predicted power output
    """
    # Avoid division by zero for very small t
    t = np.array(t)
    t[t == 0] = 1e-6  # Replace 0 with a very small number
    return CP + W_prime / t


def extract_mmp_data(
    all_activities_df: pd.DataFrame, intervals: list[int]
) -> list[tuple[int, float]]:
    """
    Extract Maximal Mean Power (MMP).

    This is extracted from the power curve data points for specified intervals
    from all activities.

    Args:
        all_activities_df: DataFrame of all processed activities,
            including power curve metrics.
        intervals: List of durations (in seconds) for which to extract MMP.

    Returns:
        List of (duration, MMP) tuples.
    """
    mmp_data = []
    for interval_sec in intervals:
        col_name = f"power_curve_{interval_name_from_seconds(interval_sec)}"
        if col_name in all_activities_df.columns:
            max_mmp = all_activities_df[col_name].max()
            if pd.notna(max_mmp) and max_mmp > 0:
                mmp_data.append((interval_sec, max_mmp))
    return mmp_data


def estimate_cp_wprime(mmp_data: list[tuple[int, float]]) -> dict[str, float]:
    """
    Estimate Critical Power (CP) and W' (Watt-Prime).

    This is done by fitting a hyperbolic model to Maximal Mean Power (MMP) data
    points.

    Args:
        mmp_data: List of (duration, power) tuples

    Returns:
        Dictionary with 'cp', 'w_prime', and 'r_squared' keys
    """
    if len(mmp_data) < 2:  # Need at least two points to fit a curve
        return {"cp": np.nan, "w_prime": np.nan, "r_squared": np.nan}

    durations = np.array([d for d, p in mmp_data])
    powers = np.array([p for d, p in mmp_data])

    # Initial guess for CP and W'
    # CP can be estimated as the lowest MMP,
    # W' as (highest MMP - lowest MMP) * shortest duration
    initial_cp = powers.min() if len(powers) > 0 else 150.0
    initial_w_prime = (
        (powers.max() - powers.min()) * durations.min() if len(powers) > 0 else 15000.0
    )

    # Ensure initial_cp is not negative or zero
    if initial_cp <= 0:
        initial_cp = 1.0
    if initial_w_prime <= 0:
        initial_w_prime = 1.0

    try:
        # Fit the curve
        # pylint: disable=unbalanced-tuple-unpacking
        popt, pcov = curve_fit(
            hyperbolic_model,
            durations,
            powers,
            p0=[initial_cp, initial_w_prime],
            bounds=([0, 0], [np.inf, np.inf]),
        )  # Bounds to ensure positive CP and W'
        cp_estimate, w_prime_estimate = popt

        # Calculate R-squared (coefficient of determination)
        predicted = hyperbolic_model(durations, cp_estimate, w_prime_estimate)
        ss_res = np.sum((powers - predicted) ** 2)
        ss_tot = np.sum((powers - np.mean(powers)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan

        return {"cp": cp_estimate, "w_prime": w_prime_estimate, "r_squared": r_squared}
    except RuntimeError as e:
        print(f"Error fitting CP/W' model: {e}")
        return {"cp": np.nan, "w_prime": np.nan, "r_squared": np.nan}
    except ValueError as e:
        print(f"Value error in CP/W' model fitting: {e}")
        return {"cp": np.nan, "w_prime": np.nan, "r_squared": np.nan}


def interval_name_from_seconds(seconds: int) -> str:
    """
    Convert duration in seconds to interval name.

    Args:
        seconds: Duration in seconds

    Returns:
        Interval name (e.g., "1min", "5min", "20sec")
    """
    if seconds < 60:
        return f"{seconds}sec"
    if seconds == 60:
        return "1min"
    if seconds == 120:
        return "2min"
    if seconds == 300:
        return "5min"
    if seconds == 600:
        return "10min"
    if seconds == 900:
        return "15min"
    if seconds == 1200:
        return "20min"
    if seconds == 1800:
        return "30min"
    if seconds == 3600:
        return "1hr"
    return f"{seconds}sec"  # Fallback for other durations
