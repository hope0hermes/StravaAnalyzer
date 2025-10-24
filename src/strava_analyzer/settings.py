"""Application settings and configuration management."""

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import GradeAdjustmentConfig, HeartRateZoneConfig, HrTssConfig


class Settings(BaseSettings):
    """
    Application settings for Strava Analyzer.

    Settings are loaded in the following order of precedence (highest to lowest):
    1. Environment variables (e.g., STRAVA_ANALYZER_DATA_DIR)
    2. .env file (if found)
    3. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="STRAVA_ANALYZER_", env_file=".env", extra="ignore"
    )

    # --- File Paths ---
    data_dir: Path = Path("data")  # Default relative path, overridden by config
    activities_file: Path = Path(
        "activities.csv"
    )  # Default relative path, overridden by config
    streams_dir: Path = Path("Streams")  # Default relative path, overridden by config

    processed_data_dir: Path = Path(
        "processed_data"
    )  # Default relative path, overridden by config
    activities_enriched_file: Path | None = (
        None  # Will be set based on processed_data_dir
    )
    daily_summary_file: Path | None = None  # Will be set based on processed_data_dir

    def __init__(self, **data):
        """Initialize the Settings object."""
        super().__init__(**data)
        # Set processed file paths based on processed_data_dir
        if self.processed_data_dir:
            if self.activities_enriched_file is None:
                self.activities_enriched_file = (
                    self.processed_data_dir / "activities_enriched.csv"
                )
            if self.daily_summary_file is None:
                self.daily_summary_file = self.processed_data_dir / "daily_summary.csv"

    # --- Activity Stream Columns Configuration ---
    # Essential columns that must be present for basic functionality
    stream_essential_columns: list[str] = [
        "time",  # Required for all temporal calculations
        "moving",  # Required to filter non-moving periods
    ]

    # Optional columns used for specific metrics, missing columns will skip related
    # calculations
    stream_optional_columns: dict[str, list[str]] = {
        "power": ["watts"],  # Power metrics
        "heartrate": ["heartrate"],  # Heart rate metrics
        "location": ["latlng", "distance"],  # GPS and distance metrics
        "gradient": ["grade_smooth", "altitude"],  # Climbing metrics
        "cadence": ["cadence"],  # Cadence analysis
        "speed": ["velocity_smooth"],  # Speed metrics
    }

    # --- Speed Zones (example, adjust as needed) ---
    speed_zones: dict[str, tuple[float, float]] = {
        "speed_zone_1": (0, 10),
        "speed_zone_2": (10, 20),
        "speed_zone_3": (20, 30),
        "speed_zone_4": (30, float("inf")),
    }

    # --- Power Zones (based on 285W FTP) ---
    # These should ideally be dynamic based on the athlete's current FTP
    power_zones: dict[str, tuple[float, float]] = {
        "power_zone_1": (0, 157),
        "power_zone_2": (158, 214),
        "power_zone_3": (215, 256),
        "power_zone_4": (257, 300),
        "power_zone_5": (301, 342),
        "power_zone_6": (343, float("inf")),
    }

    # --- Heart Rate Zones (example, adjust as needed) ---
    hr_zone_ranges: dict[str, tuple[float, float]] = {
        "hr_zone_1": (39, 110),
        "hr_zone_2": (111, 129),
        "hr_zone_3": (130, 147),
        "hr_zone_4": (148, 166),
        "hr_zone_5": (167, float("inf")),
    }

    # --- Cadence Zones (example, adjust as needed) ---
    cadence_zones: dict[str, tuple[float, float]] = {
        "cadence_50-70": (50, 70),
        "cadence_70-80": (71, 80),
        "cadence_80-90": (81, 90),
        "cadence_90-100": (91, 100),
        "cadence_100-120": (101, 120),
    }

    # --- Slope Categories (example, adjust as needed) ---
    slope_categories: dict[str, tuple[float, float]] = {
        "slope_0": (-float("inf"), 0),
        "slope_3": (1, 3),
        "slope_6": (4, 6),
        "slope_9": (7, 9),
        "slope_12": (10, 12),
        "slope_15": (13, 15),
        "slope_hors": (16, float("inf")),
    }

    # --- Power Curve Intervals (in seconds) ---
    power_curve_intervals: dict[str, int] = {
        "1sec": 1,
        "2sec": 2,
        "5sec": 5,
        "10sec": 10,
        "15sec": 15,
        "20sec": 20,
        "30sec": 30,
        "1min": 60,
        "2min": 120,
        "5min": 300,
        "10min": 600,
        "15min": 900,
        "20min": 1200,
        "30min": 1800,
        "1hr": 3600,
    }

    # --- Running Metrics Configuration ---
    fthr: float = 170  # Default FTHR, should be overridden by user
    ftpace: float = 5.0  # Default FTPace in min/km, should be overridden by user
    ftp: float = 285  # Default FTP in watts, should be overridden by user

    # Running-specific configuration models
    grade_adjustment: GradeAdjustmentConfig = GradeAdjustmentConfig(
        uphill_factor=0.5, downhill_factor=0.3, grade_smoothing_window=30
    )

    hr_zones: HeartRateZoneConfig = HeartRateZoneConfig(
        zone1_upper=0.60,  # Recovery
        zone2_upper=0.70,  # Endurance
        zone3_upper=0.80,  # Tempo
        zone4_upper=0.90,  # Threshold
        zone5_upper=1.00,  # VO2max
    )

    hr_tss: HrTssConfig = HrTssConfig(
        zone1_factor=0.6,
        zone2_factor=0.8,
        zone3_factor=1.0,
        zone4_factor=1.2,
        zone5_factor=1.5,
        zone6_factor=2.0,
    )

    # --- FTP Estimation Configuration ---
    ftp_estimation_factor: float = 0.95
    ftpace_estimation_factor: float = 0.93
    ftp_rolling_window_days: int = 42

    # --- Longitudinal Metrics Configuration ---
    atl_days: int = 7
    ctl_days: int = 28  # Aligned with Analysis_plan.md

    # --- Rider Weight (Placeholder) ---
    rider_weight_kg: float = 77.0


def load_settings(config_file: Path | None = None) -> Settings:
    """Load settings from a YAML file, environment variables, and defaults."""
    if config_file:
        with open(config_file, encoding="utf-8") as f:
            yaml_settings = yaml.safe_load(f)

        # Ensure data_dir exists and is absolute
        data_dir = Path(yaml_settings.get("data_dir", "")).expanduser().resolve()
        if not data_dir.is_absolute():
            data_dir = config_file.parent / data_dir

        # Join relative paths with data_dir
        if (
            "activities_file" in yaml_settings
            and not Path(yaml_settings["activities_file"]).is_absolute()
        ):
            yaml_settings["activities_file"] = str(
                data_dir / yaml_settings["activities_file"]
            )
        if (
            "streams_dir" in yaml_settings
            and not Path(yaml_settings["streams_dir"]).is_absolute()
        ):
            yaml_settings["streams_dir"] = str(data_dir / yaml_settings["streams_dir"])

        # Handle processed data paths similarly
        processed_dir = (
            Path(yaml_settings.get("processed_data_dir", "")).expanduser().resolve()
        )
        if not processed_dir.is_absolute():
            processed_dir = config_file.parent / processed_dir

        # Create a Settings object from YAML, then merge with env vars/defaults
        return Settings(**yaml_settings)

    return Settings()
