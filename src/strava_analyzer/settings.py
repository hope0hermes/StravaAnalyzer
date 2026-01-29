"""Application settings and configuration management."""

from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import GradeAdjustmentConfig


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

        # Recalculate power zones based on current FTP
        self._compute_power_zones()

        # Recalculate HR zones based on current FTHR
        self._compute_hr_zones()

    def _compute_power_zones(self) -> None:
        """
        Compute power zones dynamically based on physiological thresholds.

        If lt1_power and lt2_power from stress test are available, uses LT-based 7-zone model:
        - Z1: 0 to LT1 (recovery)
        - Z2: LT1 to ~(LT1+LT2)/2 (endurance)
        - Z3: ~(LT1+LT2)/2 to LT2 (sweet spot)
        - Z4: LT2 to ~110% LT2 (threshold)
        - Z5: ~110% LT2 to ~125% LT2 (VO2max)
        - Z6: ~125% LT2 to ~150% LT2 (anaerobic)
        - Z7: ~150% LT2+ (sprint/max)

        Otherwise falls back to Coggan's percentage-based 7-zone model based on FTP.
        """
        if self.ftp <= 0:
            # If FTP not set, don't override existing zones
            return

        # Use LT-based model if LT1 and LT2 power are provided
        if self.lt1_power is not None and self.lt2_power is not None:
            lt1 = int(self.lt1_power)
            lt2 = int(self.lt2_power)

            # Extrapolate zones around the lactate thresholds
            midpoint = int((lt1 + lt2) / 2)
            z4_upper = int(lt2 * 1.10)
            z5_upper = int(lt2 * 1.25)
            z6_upper = int(lt2 * 1.50)

            self.power_zones = {
                "power_zone_1": (0, lt1),  # Recovery: below LT1
                "power_zone_2": (lt1, midpoint),  # Endurance: LT1 to midpoint
                "power_zone_3": (midpoint, lt2),  # Sweet Spot: midpoint to LT2
                "power_zone_4": (lt2, z4_upper),  # Threshold: LT2 to 110% LT2
                "power_zone_5": (z4_upper, z5_upper),  # VO2max: 110% to 125% LT2
                "power_zone_6": (z5_upper, z6_upper),  # Anaerobic: 125% to 150% LT2
                "power_zone_7": (z6_upper, float("inf")),  # Sprint: 150%+ LT2
            }
        else:
            # Fallback to Coggan's percentage-based 7-zone model
            self.power_zones = {
                "power_zone_1": (0, int(0.55 * self.ftp)),
                "power_zone_2": (int(0.55 * self.ftp), int(0.75 * self.ftp)),
                "power_zone_3": (int(0.75 * self.ftp), int(0.90 * self.ftp)),
                "power_zone_4": (int(0.90 * self.ftp), int(1.05 * self.ftp)),
                "power_zone_5": (int(1.05 * self.ftp), int(1.20 * self.ftp)),
                "power_zone_6": (int(1.20 * self.ftp), int(1.50 * self.ftp)),
                "power_zone_7": (int(1.50 * self.ftp), float("inf")),
            }

    def _compute_hr_zones(self) -> None:
        """
        Compute HR zones dynamically based on physiological thresholds.

        Uses a LT-based 5-zone model when LT1/LT2 are available:
        - Z1 (Recovery): 0 to LT1
        - Z2 (Endurance): LT1 to LT2
        - Z3 (Threshold): LT2 to FTHR
        - Z4 (VO2max): FTHR to MaxHR
        - Z5 (Max): MaxHR+

        Falls back to percentage-based model if LT values not available.
        """
        if self.fthr <= 0:
            # If FTHR not set, don't override existing zones
            return

        # Use LT-based model if LT1 and LT2 are provided
        if self.lt1_hr is not None and self.lt2_hr is not None:
            # Estimate max HR as FTHR + ~6 bpm (typical for cycling)
            max_hr = int(self.fthr + 6)

            self.hr_zone_ranges = {
                "hr_zone_1": (0, int(self.lt1_hr)),  # Recovery: below LT1
                "hr_zone_2": (int(self.lt1_hr), int(self.lt2_hr)),  # Endurance: LT1 to LT2
                "hr_zone_3": (int(self.lt2_hr), int(self.fthr)),  # Threshold: LT2 to FTHR
                "hr_zone_4": (int(self.fthr), max_hr),  # VO2max: FTHR to MaxHR
                "hr_zone_5": (max_hr, float("inf")),  # Max: above MaxHR
            }
        else:
            # Fallback to Coggan's percentage-based 5-zone model
            self.hr_zone_ranges = {
                "hr_zone_1": (0, int(0.85 * self.fthr)),
                "hr_zone_2": (int(0.85 * self.fthr), int(0.95 * self.fthr)),
                "hr_zone_3": (int(0.95 * self.fthr), int(1.05 * self.fthr)),
                "hr_zone_4": (int(1.05 * self.fthr), int(1.20 * self.fthr)),
                "hr_zone_5": (int(1.20 * self.fthr), float("inf")),
            }

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
    # Using Coggan's 7-zone model (computed dynamically in __init__)
    power_zones: dict[str, tuple[float, float]] = {
        "power_zone_1": (0, 157),
        "power_zone_2": (157, 214),
        "power_zone_3": (214, 256),
        "power_zone_4": (256, 299),
        "power_zone_5": (299, 342),
        "power_zone_6": (342, 427),
        "power_zone_7": (427, float("inf")),
    }

    # --- Heart Rate Zones (computed dynamically in __init__) ---
    # Default values are overwritten by _compute_hr_zones()
    hr_zone_ranges: dict[str, tuple[float, float]] = {
        "hr_zone_1": (0, 129),
        "hr_zone_2": (129, 155),
        "hr_zone_3": (155, 170),
        "hr_zone_4": (170, 176),
        "hr_zone_5": (176, float("inf")),
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
        "90min": 5400,
        "2hr": 7200,
        "3hr": 10800,
        "4hr": 14400,
        "5hr": 18000,
        "6hr": 21600,
    }

    # --- Power Curve Model Configuration ---
    # Rolling window for CP/W' estimation (days)
    cp_window_days: int = 90  # Look back this many days to find peak efforts for CP model

    # --- Running Metrics Configuration ---
    fthr: float = 170  # Default FTHR, should be overridden by user
    lt1_hr: float | None = None  # Lactate Threshold 1 HR (lower threshold, from stress test)
    lt2_hr: float | None = None  # Lactate Threshold 2 HR (upper threshold, from stress test)
    ftpace: float = 5.0  # Default FTPace in min/km, should be overridden by user
    ftp: float = 285  # Default FTP in watts, should be overridden by user

    # --- Critical Power & Anaerobic Capacity ---
    # Used for W' balance calculations and anaerobic capacity modeling
    cp: float = 0.0  # Critical Power in watts (0 = disabled). Estimate: FTP × 0.88
    w_prime: float = 0.0  # W-prime (anaerobic capacity) in joules (0 = disabled). Typical: 20,000 J

    # --- Cycling Power Lactate Thresholds (from stress test) ---
    lt1_power: float | None = None  # Power at LT1 (lower threshold), from stress test
    lt2_power: float | None = None  # Power at LT2 (upper threshold), from stress test

    # Running-specific configuration models
    grade_adjustment: GradeAdjustmentConfig = GradeAdjustmentConfig(
        uphill_factor=0.5, downhill_factor=0.3, grade_smoothing_window=30
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

    def get_power_zone_edges(self) -> list[float]:
        """
        Get power zone right edges (upper boundaries) in ascending order.

        Returns only the right edges, excluding infinity.

        Returns:
            List of power zone right edge values
        """
        edges = []
        for zone_name, (left, right) in self.power_zones.items():
            if right != float("inf"):
                edges.append(float(right))
        return sorted(edges)

    def get_hr_zone_edges(self) -> list[float]:
        """
        Get HR zone right edges (upper boundaries) in ascending order.

        Returns only the right edges, excluding infinity.

        Returns:
            List of HR zone right edge values
        """
        edges = []
        for zone_name, (left, right) in self.hr_zone_ranges.items():
            if right != float("inf"):
                edges.append(float(right))
        return sorted(edges)


def load_settings(config_file: Path | None = None) -> Settings:
    """Load settings from a YAML file, environment variables, and defaults."""
    if config_file:
        # Ensure config_file is absolute path
        config_file = Path(config_file).expanduser().resolve()

        with open(config_file, encoding="utf-8") as f:
            yaml_settings = yaml.safe_load(f)

        # Ensure data_dir exists and is absolute
        data_dir_str = yaml_settings.get("data_dir", "")
        data_dir = Path(data_dir_str).expanduser()

        # If relative, join with config file's parent directory
        if not data_dir.is_absolute():
            data_dir = config_file.parent / data_dir

        # Now resolve to absolute path
        data_dir = data_dir.resolve()

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
        processed_dir_str = yaml_settings.get("processed_data_dir", "")
        processed_dir = Path(processed_dir_str).expanduser()

        # If relative, join with config file's parent directory
        if not processed_dir.is_absolute():
            processed_dir = config_file.parent / processed_dir

        # Now resolve to absolute path
        processed_dir = processed_dir.resolve()

        # Update yaml_settings with resolved path so Settings uses the correct path
        yaml_settings["processed_data_dir"] = str(processed_dir)

        # Create a Settings object from YAML, then merge with env vars/defaults
        return Settings(**yaml_settings)

    return Settings()
