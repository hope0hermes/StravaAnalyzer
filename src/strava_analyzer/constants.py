"""
Constants used throughout the Strava Analyzer package.

This module centralizes all magic numbers and commonly used values to improve
maintainability and clarity.
"""

from typing import Final


# === Time Constants ===
class TimeConstants:
    """Time-related constants in seconds."""

    SECONDS_PER_MINUTE: Final[int] = 60
    SECONDS_PER_HOUR: Final[int] = 3600
    SECONDS_PER_DAY: Final[int] = 86400

    # Gap detection for stopped periods
    GAP_DETECTION_THRESHOLD: Final[float] = 2.0  # Time gap >2s indicates stopped period

    # Rolling window sizes
    NORMALIZED_POWER_WINDOW: Final[int] = 30  # 30 seconds for NP calculation
    FTP_ESTIMATION_WINDOW: Final[int] = 1200  # 20 minutes for FTP estimation
    FTPACE_ESTIMATION_WINDOW: Final[int] = 600  # 10 minutes for FTPace estimation
    GRADE_SMOOTHING_WINDOW: Final[int] = 30  # 30 seconds for grade smoothing

    # Minimum durations
    MIN_ACTIVITY_DURATION: Final[int] = 60  # 1 minute minimum
    MIN_FTPACE_ESTIMATION_DURATION: Final[int] = 600  # 10 minutes for FTPace
    MIN_DECOUPLING_DURATION: Final[int] = 3600  # 1 hour for decoupling analysis
    MIN_ROLLING_CALCULATION: Final[int] = 60  # 1 minute for rolling calculations


# === Threshold Estimation Factors ===
class ThresholdFactors:
    """Factors used for threshold estimation."""

    FTP_FROM_20MIN: Final[float] = 0.95  # FTP = 95% of 20-min max power
    FTPACE_FROM_10MIN: Final[float] = 0.93  # FTPace = 93% of 10-min max pace
    COASTING_THRESHOLD_FACTOR: Final[float] = 0.50  # 50% of FTP for coasting detection


# === Training Load Windows ===
class TrainingLoadWindows:
    """Windows for training load calculations."""

    ATL_DAYS: Final[int] = 7  # Acute Training Load (Fatigue)
    CTL_DAYS: Final[int] = 42  # Chronic Training Load (Fitness)
    FTP_ROLLING_WINDOW_DAYS: Final[int] = 42  # Days to look back for FTP

    # Alternative CTL windows
    CTL_DAYS_CONSERVATIVE: Final[int] = 28  # More conservative CTL window


# === Zone Percentages (Coggan 7-Zone Model) ===
class PowerZoneThresholds:
    """Power zone boundaries as percentages of FTP."""

    ZONE_1_MAX: Final[float] = 0.55  # Active Recovery
    ZONE_2_MAX: Final[float] = 0.75  # Endurance
    ZONE_3_MAX: Final[float] = 0.90  # Tempo
    ZONE_4_MAX: Final[float] = 1.05  # Threshold
    ZONE_5_MAX: Final[float] = 1.20  # VO2 Max
    ZONE_6_MAX: Final[float] = 1.50  # Anaerobic Capacity
    # Zone 7 is everything above 1.50


# === Heart Rate Zone Thresholds ===
class HeartRateZoneThresholds:
    """Heart rate zone boundaries as percentages of FTHR."""

    ZONE_1_MAX: Final[float] = 0.82  # Recovery
    ZONE_2_MAX: Final[float] = 0.89  # Aerobic
    ZONE_3_MAX: Final[float] = 0.94  # Tempo
    ZONE_4_MAX: Final[float] = 1.00  # Threshold
    # Zone 5 is everything above 1.00


# === Efficiency Calculation ===
class EfficiencyConstants:
    """Constants for efficiency metrics."""

    MIN_VALID_POWER: Final[float] = 0.0  # Minimum power to consider valid
    MIN_VALID_HR: Final[float] = 30.0  # Minimum HR to consider valid (bpm)
    MIN_VALID_VELOCITY: Final[float] = 0.1  # Minimum velocity (m/s)

    DECOUPLING_MIN_DURATION: Final[int] = TimeConstants.MIN_DECOUPLING_DURATION


# === Data Validation ===
class ValidationThresholds:
    """Thresholds for data validation."""

    MIN_POWER_FOR_METRICS: Final[int] = 30  # Minimum data points for power metrics
    MIN_HR_BPM: Final[int] = 30  # Minimum valid heart rate
    MAX_HR_BPM: Final[int] = 220  # Maximum valid heart rate
    MIN_POWER_WATTS: Final[float] = 0.0  # Minimum valid power
    MAX_POWER_WATTS: Final[float] = 3000.0  # Maximum realistic power
    MIN_CADENCE: Final[float] = 0.0  # Minimum cadence
    MAX_CADENCE: Final[float] = 250.0  # Maximum realistic cadence
    MIN_VELOCITY_MS: Final[float] = 0.0  # Minimum velocity (m/s)
    MAX_VELOCITY_MS: Final[float] = 30.0  # Maximum realistic velocity (~108 km/h)


# === Grade Adjustment (Running) ===
class GradeAdjustmentFactors:
    """Factors for grade-based pace adjustments in running."""

    UPHILL_FACTOR: Final[float] = 0.5  # Pace adjustment for uphill
    DOWNHILL_FACTOR: Final[float] = 0.3  # Pace adjustment for downhill


# === TSS Calculation Constants ===
class TSSConstants:
    """Constants for Training Stress Score calculations."""

    TSS_NORMALIZATION_FACTOR: Final[int] = 100  # Multiply by 100 for TSS
    TSS_HOUR_DIVISOR: Final[int] = TimeConstants.SECONDS_PER_HOUR

    # HR-TSS zone stress factors
    HR_ZONE_1_FACTOR: Final[float] = 0.6
    HR_ZONE_2_FACTOR: Final[float] = 0.8
    HR_ZONE_3_FACTOR: Final[float] = 1.0
    HR_ZONE_4_FACTOR: Final[float] = 1.2
    HR_ZONE_5_FACTOR: Final[float] = 1.5
    HR_ZONE_6_FACTOR: Final[float] = 2.0


# === Power Curve Durations ===
class PowerCurveDurations:
    """Standard durations for power curve analysis (in seconds)."""

    DURATION_5S: Final[int] = 5
    DURATION_10S: Final[int] = 10
    DURATION_20S: Final[int] = 20
    DURATION_30S: Final[int] = 30
    DURATION_1MIN: Final[int] = 60
    DURATION_2MIN: Final[int] = 120
    DURATION_5MIN: Final[int] = 300
    DURATION_10MIN: Final[int] = 600
    DURATION_20MIN: Final[int] = 1200
    DURATION_30MIN: Final[int] = 1800
    DURATION_1HR: Final[int] = 3600
    DURATION_2HR: Final[int] = 7200
    DURATION_5HR: Final[int] = 18000

    @classmethod
    def get_standard_durations(cls) -> dict[str, int]:
        """Get all standard durations as a dictionary."""
        return {
            "5s": cls.DURATION_5S,
            "10s": cls.DURATION_10S,
            "20s": cls.DURATION_20S,
            "30s": cls.DURATION_30S,
            "1min": cls.DURATION_1MIN,
            "2min": cls.DURATION_2MIN,
            "5min": cls.DURATION_5MIN,
            "10min": cls.DURATION_10MIN,
            "20min": cls.DURATION_20MIN,
            "30min": cls.DURATION_30MIN,
            "1hr": cls.DURATION_1HR,
            "2hr": cls.DURATION_2HR,
            "5hr": cls.DURATION_5HR,
        }


# === Training Status Thresholds ===
class TrainingStatusThresholds:
    """Thresholds for determining training status."""

    # ACWR (Acute:Chronic Workload Ratio) thresholds
    ACWR_HIGH_RISK: Final[float] = 1.3  # Above this = high injury risk
    ACWR_LOW_TRAINING: Final[float] = 0.8  # Below this = undertraining

    # TSB (Training Stress Balance) thresholds
    TSB_FRESH: Final[float] = 15.0  # Above this = fresh/ready for performance
    TSB_HIGH_FATIGUE: Final[float] = -30.0  # Below this = high fatigue
    TSB_PRODUCTIVE_MIN: Final[float] = -30.0  # Productive training range
    TSB_PRODUCTIVE_MAX: Final[float] = -10.0


# === CSV Parsing ===
class CSVConstants:
    """Constants for CSV file parsing."""

    DEFAULT_SEPARATOR: Final[str] = ";"  # Semicolon-separated format
    DEFAULT_ENCODING: Final[str] = "utf-8"


# === Metric Name Prefixes ===
class MetricPrefixes:
    """Standard prefixes for metric names."""

    RAW: Final[str] = "raw_"
    MOVING: Final[str] = "moving_"

    # Zone prefixes
    POWER_ZONE: Final[str] = "power_zone_"
    HR_ZONE: Final[str] = "hr_zone_"
    CADENCE_ZONE: Final[str] = "cadence_zone_"
    SPEED_ZONE: Final[str] = "speed_zone_"
    SLOPE_ZONE: Final[str] = "slope_zone_"


# === File Extensions ===
class FileExtensions:
    """Common file extensions."""

    CSV: Final[str] = ".csv"
    JSON: Final[str] = ".json"
    YAML: Final[str] = ".yaml"
    YML: Final[str] = ".yml"
