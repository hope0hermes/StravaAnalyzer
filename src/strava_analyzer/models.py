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
    aei: float | None = Field(None, description="Anaerobic Energy Index (kJ/kg)")


class ActivityType(str, Enum):
    """Supported activity types."""

    RIDE = "Ride"
    VIRTUAL_RIDE = "VirtualRide"
    RUN = "Run"
    WALK = "Walk"


# ActivityStream is a typed alias for a pandas DataFrame containing the activity
# time-series streams (columns like "time", "watts", "heartrate", etc.). Using
# DataFrame preserves pandas operations and avoids duplicating DataFrame-like
# behavior in a Pydantic model.
ActivityStream = DataFrame


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
