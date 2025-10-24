"""
Shared pytest fixtures for StravaAnalyzer tests.

This module provides reusable fixtures for:
- Test data (activities, streams)
- Settings configurations
- Temporary directories
- Sample DataFrames
"""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from strava_analyzer.settings import Settings

# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary YAML config file for testing."""
    config_path = tmp_path / "config.yaml"
    return config_path


@pytest.fixture
def sample_config_dict() -> dict:
    """Provide a sample configuration dictionary."""
    return {
        "ftp": 285,
        "fthr": 170,
        "ftpace": 5.0,
        "rider_weight_kg": 77.0,
        "data_dir": "data",
        "activities_file": "activities.csv",
        "streams_dir": "Streams",
        "processed_data_dir": "processed_data",
        "power_zones": {
            "power_zone_1": [0, 157],
            "power_zone_2": [158, 214],
            "power_zone_3": [215, 256],
            "power_zone_4": [257, 300],
            "power_zone_5": [301, 342],
            "power_zone_6": [343, 9999],
        },
        "hr_zone_ranges": {
            "hr_zone_1": [39, 110],
            "hr_zone_2": [111, 129],
            "hr_zone_3": [130, 147],
            "hr_zone_4": [148, 166],
            "hr_zone_5": [167, 999],
        },
    }


@pytest.fixture
def sample_config_file(tmp_path: Path, sample_config_dict: dict) -> Path:
    """Create a temporary config file with sample data."""
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config_dict, f)
    return config_path


@pytest.fixture
def settings_with_ftp() -> Settings:
    """Provide settings with FTP=285W and FTHR=170bpm."""
    return Settings(ftp=285, fthr=170, rider_weight_kg=77.0)


# ============================================================================
# Data Fixtures - Streams
# ============================================================================


@pytest.fixture
def simple_stream() -> pd.DataFrame:
    """
    Provide a simple stream with 5 data points.

    Useful for basic testing of calculators.
    """
    return pd.DataFrame(
        {
            "time": [0, 1, 2, 3, 4],
            "watts": [200, 250, 300, 250, 200],
            "heartrate": [140, 150, 160, 155, 145],
            "moving": [True, True, True, True, True],
            "distance": [0.0, 8.0, 16.0, 24.0, 32.0],
            "altitude": [100.0, 102.0, 105.0, 108.0, 110.0],
        }
    )


@pytest.fixture
def stream_with_zeros() -> pd.DataFrame:
    """
    Provide a stream with zero power periods.

    Useful for testing stopped time handling.
    """
    return pd.DataFrame(
        {
            "time": [0, 1, 2, 3, 4, 5, 6, 7, 8],
            "watts": [200, 250, 0, 0, 0, 250, 300, 250, 200],
            "heartrate": [140, 150, 145, 140, 138, 150, 160, 155, 145],
            "moving": [True, True, False, False, False, True, True, True, True],
            "distance": [0.0, 8.0, 8.0, 8.0, 8.0, 16.0, 24.0, 32.0, 40.0],
        }
    )


@pytest.fixture
def realistic_stream() -> pd.DataFrame:
    """
    Provide a realistic stream with 120 data points (2 minutes).

    Useful for testing time-weighted averaging and metric calculations.
    """

    time = list(range(120))
    # Simulate varying power: warmup, intervals, cooldown (must be 120 values)
    watts = (
        [150] * 20  # Warmup (20)
        + [280, 290, 300, 310, 300, 290, 280, 270] * 5  # Intervals (40)
        + [200] * 40  # Recovery (40)
        + [150] * 20  # Cooldown (20)
    )  # Total: 120

    # HR gradually increases then decreases (must be 120 values)
    heartrate = (
        list(range(120, 140))  # Warmup (20)
        + [140 + i % 20 for i in range(40)]  # Intervals (40)
        + list(range(160, 140, -1))  # Recovery (20)
        + list(range(140, 120, -1))  # Cooldown (20)
    )  # Total: 100
    heartrate += [120] * 20  # Extend to 120

    moving = [True] * 120
    distance = [i * 8.0 for i in range(120)]  # 8m/s = ~28.8 km/h
    altitude = [100.0 + i * 0.5 for i in range(120)]  # Gentle climb

    return pd.DataFrame(
        {
            "time": time,
            "watts": watts,
            "heartrate": heartrate,
            "moving": moving,
            "distance": distance,
            "altitude": altitude,
            "cadence": [80 + (i % 10) for i in range(120)],
        }
    )


@pytest.fixture
def stream_with_gaps() -> pd.DataFrame:
    """
    Provide a stream with time gaps (stopped periods).

    Useful for testing time-weighted averaging with gaps.
    """
    return pd.DataFrame(
        {
            "time": [0, 1, 2, 3, 154, 155, 156, 157],  # Gap from 3 to 154
            "watts": [200, 250, 300, 0, 250, 300, 250, 200],
            "heartrate": [140, 150, 160, 140, 150, 160, 155, 145],
            "moving": [True, True, True, False, True, True, True, True],
            "distance": [0.0, 8.0, 16.0, 16.0, 24.0, 32.0, 40.0, 48.0],
        }
    )


@pytest.fixture
def stream_hr_only() -> pd.DataFrame:
    """Provide a stream with heart rate but no power."""
    return pd.DataFrame(
        {
            "time": [0, 1, 2, 3, 4],
            "heartrate": [140, 150, 160, 155, 145],
            "moving": [True, True, True, True, True],
            "distance": [0.0, 8.0, 16.0, 24.0, 32.0],
        }
    )


@pytest.fixture
def stream_power_only() -> pd.DataFrame:
    """Provide a stream with power but no heart rate."""
    return pd.DataFrame(
        {
            "time": [0, 1, 2, 3, 4],
            "watts": [200, 250, 300, 250, 200],
            "moving": [True, True, True, True, True],
            "distance": [0.0, 8.0, 16.0, 24.0, 32.0],
        }
    )


# ============================================================================
# Data Fixtures - Activities
# ============================================================================


@pytest.fixture
def sample_activity() -> dict:
    """Provide a sample activity dictionary."""
    return {
        "id": 12345678,
        "name": "Morning Ride",
        "type": "Ride",
        "start_date": "2024-01-15T08:30:00Z",
        "distance": 25000,  # meters
        "moving_time": 3600,  # seconds
        "total_time": 3900,
        "elevation_gain": 250,
        "average_speed": 6.944,  # m/s
        "max_speed": 12.5,
    }


@pytest.fixture
def sample_activities_df() -> pd.DataFrame:
    """Provide a sample activities DataFrame."""
    return pd.DataFrame(
        {
            "id": [12345678, 12345679, 12345680],
            "name": ["Morning Ride", "Evening Ride", "Weekend Long"],
            "type": ["Ride", "Ride", "Ride"],
            "start_date": pd.to_datetime(
                [
                    "2024-01-15 08:30:00",
                    "2024-01-16 18:00:00",
                    "2024-01-20 09:00:00",
                ]
            ),
            "distance": [25000, 30000, 80000],
            "moving_time": [3600, 4200, 14400],
            "total_time": [3900, 4500, 15000],
            "elevation_gain": [250, 300, 1200],
        }
    )


# ============================================================================
# Test Data Directories
# ============================================================================


@pytest.fixture
def test_data_dir() -> Path:
    """Provide path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def fixtures_dir() -> Path:
    """Provide path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_activities_csv(fixtures_dir: Path) -> Path:
    """Provide path to sample activities CSV."""
    return fixtures_dir / "sample_activities.csv"


@pytest.fixture
def sample_stream_csv(fixtures_dir: Path) -> Path:
    """Provide path to sample stream CSV."""
    return fixtures_dir / "sample_stream.csv"


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory structure."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "Streams").mkdir()
    return data_dir


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
