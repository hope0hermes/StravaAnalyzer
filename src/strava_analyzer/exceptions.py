"""
Custom exceptions for the Strava Analyzer package.

This module defines all custom exceptions used throughout the application,
providing clear error hierarchies and specific error types for different scenarios.
"""


class StravaAnalyzerError(Exception):
    """Base exception for all Strava Analyzer errors."""


class ConfigurationError(StravaAnalyzerError):
    """Raised when there is an issue with configuration settings."""


class ValidationError(StravaAnalyzerError):
    """Raised when data validation fails."""


class InvalidDataError(ValidationError):
    """Raised when input data is invalid or missing required fields."""


class CalculationError(StravaAnalyzerError):
    """Raised when there is an error during metric calculation."""


class MetricCalculationError(CalculationError):
    """Raised when there is a specific error during activity metric calculation."""


class DataLoadError(StravaAnalyzerError):
    """Raised when there is an error loading data files."""


class ProcessingError(StravaAnalyzerError):
    """Raised when there is an error processing activity data."""


class ThresholdEstimationError(StravaAnalyzerError):
    """Raised when there is an error estimating FTP, FTHR, or FTPace."""


class ActivityTypeError(StravaAnalyzerError):
    """Raised when an unsupported activity type is encountered."""


class StreamDataError(StravaAnalyzerError):
    """Raised when there are issues with activity stream data."""
