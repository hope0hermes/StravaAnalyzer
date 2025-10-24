"""Unit tests for Settings module."""

from pathlib import Path

import pytest
import yaml

from strava_analyzer.settings import Settings, load_settings


class TestSettingsBasicLoading:
    """Test basic settings loading from different sources."""

    def test_load_from_env_vars(self, monkeypatch):
        """Test that settings are correctly loaded from environment variables."""
        monkeypatch.setenv("STRAVA_ANALYZER_FTP", "300")
        monkeypatch.setenv("STRAVA_ANALYZER_FTHR", "175")
        monkeypatch.setenv("STRAVA_ANALYZER_RIDER_WEIGHT_KG", "80")

        settings = load_settings()

        assert settings.ftp == 300
        assert settings.fthr == 175
        assert settings.rider_weight_kg == 80

    def test_load_from_yaml(self, temp_config_file: Path):
        """Test that settings are correctly loaded from a YAML file."""
        config_data = {
            "ftp": 285,
            "fthr": 170,
            "rider_weight_kg": 77.0,
            "data_dir": "test_data",
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.ftp == 285
        assert settings.fthr == 170
        assert settings.rider_weight_kg == 77.0

    def test_yaml_overrides_env_vars(self, monkeypatch, temp_config_file: Path):
        """Test that YAML settings override environment variables."""
        monkeypatch.setenv("STRAVA_ANALYZER_FTP", "300")
        monkeypatch.setenv("STRAVA_ANALYZER_FTHR", "175")

        config_data = {
            "ftp": 285,
            "fthr": 170,
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.ftp == 285
        assert settings.fthr == 170

    def test_default_values(self):
        """Test that settings use default values when no config is provided."""
        settings = Settings()

        assert settings.ftp == 285  # Default FTP
        assert settings.fthr == 170  # Default FTHR
        assert settings.rider_weight_kg == 77.0
        assert settings.data_dir == Path("data")


class TestSettingsPathResolution:
    """Test path resolution and handling."""

    def test_relative_paths_resolved(self, temp_config_file: Path):
        """Test that relative paths are correctly resolved."""
        config_data = {
            "data_dir": "test_data",
            "activities_file": "activities.csv",
            "streams_dir": "Streams",
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        # The load_settings function resolves data_dir relative to config_file.parent
        # Then joins activities_file with data_dir
        # Check that activities_file is an absolute path that contains the
        # resolved data_dir
        assert settings.activities_file.is_absolute()
        assert "test_data" in str(settings.activities_file)

    def test_absolute_paths_preserved(self, temp_config_file: Path, tmp_path: Path):
        """Test that absolute paths are preserved."""
        abs_data_dir = tmp_path / "absolute_data"
        abs_data_dir.mkdir()

        config_data = {
            "data_dir": str(abs_data_dir),
            "activities_file": str(abs_data_dir / "activities.csv"),
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.data_dir == abs_data_dir

    def test_processed_data_paths_auto_created(self):
        """Test that processed data paths are automatically created."""
        settings = Settings(processed_data_dir=Path("output"))

        assert (
            settings.activities_enriched_file
            == Path("output") / "activities_enriched.csv"
        )
        assert settings.daily_summary_file == Path("output") / "daily_summary.csv"


class TestSettingsValidation:
    """Test settings validation and constraints."""

    def test_ftp_can_be_set(self):
        """Test that FTP can be set to custom value."""
        settings = Settings(ftp=300)
        assert settings.ftp == 300

    def test_fthr_can_be_set(self):
        """Test that FTHR can be set to custom value."""
        settings = Settings(fthr=180)
        assert settings.fthr == 180

    def test_weight_can_be_set(self):
        """Test that rider weight can be set to custom value."""
        settings = Settings(rider_weight_kg=85)
        assert settings.rider_weight_kg == 85

    def test_valid_power_zones(self):
        """Test that power zones are correctly loaded."""
        settings = Settings(
            power_zones={
                "power_zone_1": (0, 142),
                "power_zone_2": (143, 199),
                "power_zone_3": (200, 256),
            }
        )

        assert settings.power_zones["power_zone_1"] == (0, 142)
        assert len(settings.power_zones) == 3

    def test_valid_hr_zones(self):
        """Test that HR zones are correctly loaded."""
        settings = Settings(
            hr_zone_ranges={
                "hr_zone_1": (0, 110),
                "hr_zone_2": (111, 129),
                "hr_zone_3": (130, 147),
            }
        )

        assert settings.hr_zone_ranges["hr_zone_1"] == (0, 110)
        assert len(settings.hr_zone_ranges) == 3


class TestSettingsZoneConfiguration:
    """Test zone configuration handling."""

    def test_default_power_zones_loaded(self):
        """Test that default power zones are loaded."""
        settings = Settings(ftp=285)

        assert "power_zone_1" in settings.power_zones
        assert "power_zone_6" in settings.power_zones
        assert settings.power_zones["power_zone_1"] == (0, 157)

    def test_default_hr_zones_loaded(self):
        """Test that default HR zones are loaded."""
        settings = Settings(fthr=170)

        assert "hr_zone_1" in settings.hr_zone_ranges
        assert "hr_zone_5" in settings.hr_zone_ranges
        assert settings.hr_zone_ranges["hr_zone_1"] == (39, 110)

    def test_custom_zones_override_defaults(self, temp_config_file: Path):
        """Test that custom zones override default zones."""
        config_data = {
            "ftp": 285,
            "power_zones": {
                "power_zone_1": [0, 100],
                "power_zone_2": [101, 200],
                "power_zone_3": [201, 300],
            },
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.power_zones["power_zone_1"] == (0, 100)
        assert len(settings.power_zones) == 3


class TestSettingsEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_config_file_raises_error(self):
        """Test that missing config file raises appropriate error."""
        with pytest.raises(FileNotFoundError):
            load_settings(config_file=Path("nonexistent.yaml"))

    def test_invalid_yaml_raises_error(self, temp_config_file: Path):
        """Test that invalid YAML content raises error."""
        with open(temp_config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_settings(config_file=temp_config_file)

    def test_empty_config_file_uses_defaults(self, temp_config_file: Path):
        """Test that empty config file falls back to defaults."""
        with open(temp_config_file, "w") as f:
            f.write("{}")  # Empty YAML dict

        settings = load_settings(config_file=temp_config_file)

        assert settings.ftp == 285  # Default value
        assert settings.fthr == 170  # Default value


class TestSettingsComplexConfiguration:
    """Test complex configuration scenarios."""

    def test_load_sample_config(self, fixtures_dir: Path):
        """Test loading the sample config file."""
        sample_config = fixtures_dir / "sample_config.yaml"

        settings = load_settings(config_file=sample_config)

        assert settings.ftp == 285
        assert settings.fthr == 170
        assert settings.rider_weight_kg == 77.0
        assert len(settings.power_zones) == 6
        assert len(settings.hr_zone_ranges) == 5

    def test_all_settings_loaded_from_yaml(self, temp_config_file: Path):
        """Test that all settings can be loaded from YAML."""
        config_data = {
            "ftp": 300,
            "fthr": 175,
            "ftpace": 4.5,
            "rider_weight_kg": 80.0,
            "data_dir": "custom_data",
            "activities_file": "my_activities.csv",
            "streams_dir": "MyStreams",
            "processed_data_dir": "output",
            "atl_days": 7,
            "ctl_days": 28,
            "ftp_estimation_factor": 0.95,
        }
        with open(temp_config_file, "w") as f:
            yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.ftp == 300
        assert settings.fthr == 175
        assert settings.ftpace == 4.5
        assert settings.rider_weight_kg == 80.0
        assert settings.atl_days == 7
        assert settings.ctl_days == 28
