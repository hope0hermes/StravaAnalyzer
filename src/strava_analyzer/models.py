"""
Data models for the Strava Analyzer package.

This module defines all the core data structures used throughout the application,
ensuring type safety and data validation using Pydantic models.
"""

from datetime import datetime
from enum import Enum

from pandas import DataFrame
from pydantic import BaseModel, Field, field_validator


class MaximumMeanPowers(BaseModel):
    """Maximum mean powers for various durations."""

    durations: list[int] = Field(..., description="List of durations in seconds")
    powers: list[float] = Field(..., description="List of maximum mean powers in watts")

    @property
    def as_dict(self) -> dict[int, float]:
        """Return MMP curve as duration:power dictionary."""
        return dict(zip(self.durations, self.powers, strict=False))


class CriticalPowerModel(BaseModel):
    """Critical power model parameters."""

    cp: float = Field(..., description="Critical Power estimate in watts")
    w_prime: float = Field(..., description="W' (W prime) estimate in joules")
    r_squared: float = Field(..., description="R-squared of CP model fit")


class PowerProfile(BaseModel):
    """Complete power profile data for an activity or athlete."""

    mmp_curve: MaximumMeanPowers = Field(
        ..., description="Maximum mean power curve data"
    )
    cp_model: CriticalPowerModel | None = Field(
        None, description="Critical Power model parameters if computed"
    )
    time_to_exhaustion: dict[str, float] | None = Field(
        None, description="Time to exhaustion predictions at various powers"
    )
    aei: float | None = Field(None, description="Anaerobic Energy Index (W'/kg)")


class ActivityType(str, Enum):
    """Supported activity types."""

    RIDE = "Ride"
    VIRTUAL_RIDE = "VirtualRide"
    RUN = "Run"
    WALK = "Walk"


class PowerZones(BaseModel):
    """Power zone definitions based on FTP."""

    zone_1: tuple[float, float] = Field(..., description="Recovery zone range")
    zone_2: tuple[float, float] = Field(..., description="Endurance zone range")
    zone_3: tuple[float, float] = Field(..., description="Tempo zone range")
    zone_4: tuple[float, float] = Field(..., description="Threshold zone range")
    zone_5: tuple[float, float] = Field(..., description="VO2max zone range")
    zone_6: tuple[float, float] = Field(..., description="Anaerobic zone range")
    zone_7: tuple[float, float] = Field(..., description="Neuromuscular zone range")


class HeartRateZoneConfig(BaseModel):
    """Configuration for heart rate zones based on FTHR percentages."""

    zone1_upper: float = Field(
        0.60, description="Upper limit for Zone 1 (Recovery) as % of FTHR"
    )
    zone2_upper: float = Field(
        0.70, description="Upper limit for Zone 2 (Endurance) as % of FTHR"
    )
    zone3_upper: float = Field(
        0.80, description="Upper limit for Zone 3 (Tempo) as % of FTHR"
    )
    zone4_upper: float = Field(
        0.90, description="Upper limit for Zone 4 (Threshold) as % of FTHR"
    )
    zone5_upper: float = Field(
        1.00, description="Upper limit for Zone 5 (VO2max) as % of FTHR"
    )

    @field_validator("*")
    @classmethod
    def check_zone_ranges(cls, v: float) -> float:
        """Validate that zone percentages are in ascending order."""
        if v <= 0 or v > 1:
            raise ValueError("Zone percentage must be between 0 and 1")
        return v


class HeartRateZones(BaseModel):
    """Heart rate zone definitions based on FTHR."""

    zone_1: tuple[float, float] = Field(..., description="Recovery zone range")
    zone_2: tuple[float, float] = Field(..., description="Aerobic zone range")
    zone_3: tuple[float, float] = Field(..., description="Tempo zone range")
    zone_4: tuple[float, float] = Field(..., description="Threshold zone range")
    zone_5: tuple[float, float] = Field(..., description="Anaerobic zone range")
    zone_6: tuple[float, float] = Field(..., description="Maximum zone range")


# ActivityStream is a typed alias for a pandas DataFrame containing the activity
# time-series streams (columns like "time", "watts", "heartrate", etc.). Using
# DataFrame preserves pandas operations and avoids duplicating DataFrame-like
# behavior in a Pydantic model.
ActivityStream = DataFrame


class ActivitySummary(BaseModel):
    """Summary data for an activity."""

    id: int = Field(..., description="Unique activity ID")
    type: ActivityType = Field(..., description="Activity type")
    start_date: datetime = Field(..., description="Activity start time")
    name: str = Field(..., description="Activity name")
    distance: float = Field(..., description="Total distance in meters")
    moving_time: int = Field(..., description="Moving time in seconds")
    elapsed_time: int = Field(..., description="Elapsed time in seconds")
    total_elevation_gain: float = Field(
        ..., description="Total elevation gain in meters"
    )
    average_speed: float = Field(..., description="Average speed in m/s")
    max_speed: float = Field(..., description="Maximum speed in m/s")
    average_watts: float | None = Field(None, description="Average power in watts")
    weighted_average_watts: float | None = Field(
        None, description="Normalized power in watts"
    )
    average_heartrate: float | None = Field(
        None, description="Average heart rate in bpm"
    )
    max_heartrate: float | None = Field(None, description="Maximum heart rate in bpm")
    average_cadence: float | None = Field(None, description="Average cadence in rpm")


# PowerProfile model moved to power_profile.py


class GradeAdjustmentConfig(BaseModel):
    """Configuration for grade-based pace adjustments."""

    uphill_factor: float = Field(
        0.5, description="Adjustment factor for uphill running"
    )
    downhill_factor: float = Field(
        0.3, description="Adjustment factor for downhill running"
    )
    grade_smoothing_window: int = Field(
        30, description="Window size in seconds for grade smoothing"
    )

    @field_validator("*")
    @classmethod
    def check_factors(cls, v: float | int, info) -> float | int:
        """Validate configuration values are reasonable."""
        if info.field_name.endswith("_factor") and (v < 0 or v > 2):
            raise ValueError(f"{info.field_name} must be between 0 and 2")
        if info.field_name == "grade_smoothing_window" and (v < 5 or v > 120):
            raise ValueError("Smoothing window must be between 5 and 120 seconds")
        return v


class HrTssConfig(BaseModel):
    """Configuration for Heart Rate Training Stress Score calculation."""

    zone1_factor: float = Field(0.6, description="Stress factor for Zone 1")
    zone2_factor: float = Field(0.8, description="Stress factor for Zone 2")
    zone3_factor: float = Field(1.0, description="Stress factor for Zone 3")
    zone4_factor: float = Field(1.2, description="Stress factor for Zone 4")
    zone5_factor: float = Field(1.5, description="Stress factor for Zone 5")
    zone6_factor: float = Field(2.0, description="Stress factor for Zone 6")

    @field_validator("*")
    @classmethod
    def check_factors(cls, v: float) -> float:
        """Validate stress factors are reasonable."""
        if v < 0 or v > 3:
            raise ValueError("Stress factor must be between 0 and 3")
        return v


class RunningMetrics(BaseModel):
    """Comprehensive metrics specific to running activities."""

    # Activity identification
    id: int = Field(..., description="Unique activity ID")
    start_date: datetime = Field(..., description="Activity start time")

    # Basic metrics
    total_time_seconds: float = Field(..., description="Total time in seconds")
    moving_time_seconds: float = Field(..., description="Moving time in seconds")
    distance: float = Field(..., description="Distance in meters")
    total_elevation_gain: float = Field(
        ..., description="Total elevation gain in meters"
    )

    # Running-specific metrics
    average_ngp: float = Field(
        ..., description="Average Normalized Graded Pace in min/km"
    )
    rtss: float = Field(..., description="Running Training Stress Score")
    hrtss: float = Field(..., description="Heart Rate Training Stress Score")

    # Overall training load
    tss: float = Field(..., description="Final Training Stress Score used")
    tss_method: str = Field(..., description="Method used for TSS (rTSS or hrTSS)")

    @field_validator("tss_method")
    @classmethod
    def validate_tss_method(cls, v: str) -> str:
        """Validate TSS method is one of the allowed values."""
        allowed = {"rTSS", "hrTSS", "None"}
        if v not in allowed:
            raise ValueError(f"TSS method must be one of: {', '.join(allowed)}")
        return v


class ActivityMetrics(BaseModel):
    """Comprehensive metrics calculated for an activity."""

    # Basic metrics
    total_time: float = Field(0.0, description="Total time in seconds")
    moving_time: float = Field(0.0, description="Moving time in seconds")
    distance: float = Field(0.0, description="Distance in meters")
    elevation_gain: float = Field(0.0, description="Total elevation gain in meters")

    # Power metrics
    average_power: float | None = Field(None, description="Average power in watts")
    normalized_power: float | None = Field(
        None, description="Normalized power in watts"
    )
    intensity_factor: float | None = Field(None, description="Intensity factor")
    training_stress_score: float | None = Field(
        None, description="Training stress score"
    )
    power_per_kg: float | None = Field(None, description="Power per kilogram")

    # Heart rate metrics
    average_hr: float | None = Field(None, description="Average heart rate in bpm")
    max_hr: float | None = Field(None, description="Maximum heart rate in bpm")
    hr_training_stress: float | None = Field(
        None, description="Heart rate training stress"
    )

    # Running metrics
    normalized_graded_pace: float | None = Field(
        None, description="Normalized graded pace in min/km"
    )
    running_stress_score: float | None = Field(
        None, description="Running Training Stress Score (rTSS)"
    )
    heart_rate_stress: float | None = Field(
        None, description="Heart Rate Training Stress Score (hrTSS)"
    )
    running_metrics: RunningMetrics | None = Field(
        None, description="Detailed running-specific metrics"
    )

    # Zone distributions
    power_zones: dict[str, float] | None = Field(
        None, description="Time in power zones (%)"
    )
    hr_zones: dict[str, float] | None = Field(
        None, description="Time in heart rate zones (%)"
    )
    cadence_zones: dict[str, float] | None = Field(
        None, description="Time in cadence zones (%)"
    )
    speed_zones: dict[str, float] | None = Field(
        None, description="Time in speed zones (%)"
    )
    slope_zones: dict[str, float] | None = Field(
        None, description="Time in slope/grade categories (%)"
    )

    # Efficiency metrics
    efficiency_factor: float | None = Field(None, description="Efficiency factor")
    decoupling: float | None = Field(None, description="Power:HR decoupling")

    # Power profile
    power_profile: PowerProfile | None = Field(
        None, description="Power profile metrics"
    )


class TrainingLoadSummary(BaseModel):
    """Summary of training load metrics."""

    chronic_training_load: float = Field(..., description="CTL (42-day fitness)")
    acute_training_load: float = Field(..., description="ATL (7-day fatigue)")
    training_stress_balance: float = Field(..., description="TSB (freshness)")
    acwr: float = Field(..., description="Acute:Chronic Workload Ratio")

    @property
    def status(self) -> str:
        """Get the current training status based on TSB and ACWR."""
        from .constants import TrainingStatusThresholds

        if self.acwr > TrainingStatusThresholds.ACWR_HIGH_RISK:
            return "High Risk - Reduce Load"
        if self.acwr < TrainingStatusThresholds.ACWR_LOW_TRAINING:
            return "Undertraining"

        if self.training_stress_balance > TrainingStatusThresholds.TSB_FRESH:
            return "Fresh - Ready for Performance"
        if self.training_stress_balance < TrainingStatusThresholds.TSB_HIGH_FATIGUE:
            return "High Fatigue - Recovery Needed"
        if (
            TrainingStatusThresholds.TSB_PRODUCTIVE_MIN
            <= self.training_stress_balance
            <= TrainingStatusThresholds.TSB_PRODUCTIVE_MAX
        ):
            return "Productive Training"
        return "Maintenance"


class LongitudinalSummary(BaseModel):
    """Longitudinal performance analysis and trends."""

    period_start: datetime = Field(..., description="Start of analysis period")
    period_end: datetime = Field(..., description="End of analysis period")
    total_activities: int = Field(..., description="Total number of activities")
    total_distance: float = Field(..., description="Total distance in meters")
    total_elevation: float = Field(..., description="Total elevation gain in meters")
    total_time: float = Field(..., description="Total time in seconds")
    training_load: TrainingLoadSummary = Field(..., description="Training load metrics")
    performance_trends: dict[str, float] = Field(
        default_factory=dict, description="Performance trend metrics"
    )
    zone_distributions: dict[str, dict[str, float]] = Field(
        default_factory=dict, description="Zone distribution statistics"
    )
