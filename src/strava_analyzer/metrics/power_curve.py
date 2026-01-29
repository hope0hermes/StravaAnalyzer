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


def estimate_cp_wprime(
    mmp_data: list[tuple[int, float]], ftp: float | None = None
) -> dict[str, float]:
    """
    Estimate Critical Power (CP) and W' (Watt-Prime).

    This is done by fitting a hyperbolic model to Maximal Mean Power (MMP) data
    points. The function filters out very short durations (< 2 minutes) as they
    can distort the hyperbolic fit, and uses realistic bounds to prevent
    physiologically impossible values.

    Args:
        mmp_data: List of (duration, power) tuples
        ftp: Optional FTP value to improve initial guess for CP (typically CP ≈ 0.88 * FTP)

    Returns:
        Dictionary with 'cp', 'w_prime', and 'r_squared' keys
    """
    if len(mmp_data) < 2:  # Need at least two points to fit a curve
        return {"cp": np.nan, "w_prime": np.nan, "r_squared": np.nan}

    # Convert to arrays and filter out very short durations (< 2 minutes)
    # Short sprints can distort the hyperbolic model which is designed for
    # sustained efforts above CP
    MIN_DURATION_SEC = 120  # 2 minutes
    filtered_data = [(d, p) for d, p in mmp_data if d >= MIN_DURATION_SEC]

    # Need at least 3 points for meaningful curve fitting after filtering
    if len(filtered_data) < 3:
        return {"cp": np.nan, "w_prime": np.nan, "r_squared": np.nan}

    durations = np.array([d for d, p in filtered_data])
    powers = np.array([p for d, p in filtered_data])

    # Initial guess for CP and W'
    # If FTP is available, use it as a basis (CP ≈ 88% of FTP)
    # Otherwise, use the power at longest duration as a conservative estimate
    if ftp is not None and ftp > 0:
        initial_cp = ftp * 0.88  # CP typically ~88% of FTP
        initial_w_prime = 15000.0  # Reasonable starting point (15 kJ)
    else:
        # Use power at longest duration as conservative CP estimate
        longest_duration_idx = np.argmax(durations)
        initial_cp = powers[longest_duration_idx] * 0.95
        # Estimate W' from difference between short and long power
        initial_w_prime = (powers.max() - powers.min()) * durations.min()
        initial_w_prime = max(5000.0, min(initial_w_prime, 25000.0))

    # Ensure initial guesses are reasonable
    initial_cp = max(100.0, min(initial_cp, 400.0))
    initial_w_prime = max(5000.0, min(initial_w_prime, 30000.0))

    # Realistic physiological bounds:
    # CP: 100-400W (covers recreational to elite athletes)
    # W': 5-50 kJ (typical range for trained cyclists)
    cp_bounds = (100.0, 400.0)
    wprime_bounds = (5000.0, 50000.0)

    try:
        # Fit the curve with realistic bounds
        # pylint: disable=unbalanced-tuple-unpacking
        popt, pcov = curve_fit(
            hyperbolic_model,
            durations,
            powers,
            p0=[initial_cp, initial_w_prime],
            bounds=([cp_bounds[0], wprime_bounds[0]], [cp_bounds[1], wprime_bounds[1]]),
            maxfev=5000,  # Allow more iterations for better convergence
        )
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
        Interval name (e.g., "1min", "5min", "20sec", "2hr")
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
    if seconds == 5400:
        return "90min"
    if seconds == 7200:
        return "2hr"
    if seconds == 10800:
        return "3hr"
    if seconds == 14400:
        return "4hr"
    if seconds == 18000:
        return "5hr"
    if seconds == 21600:
        return "6hr"
    return f"{seconds}sec"  # Fallback for other durations
