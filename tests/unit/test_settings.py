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

        assert settings.ftp == 0  # Default FTP (unconfigured)
        assert settings.fthr == 0  # Default FTHR (unconfigured)
        assert settings.rider_weight_kg == 0.0
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
        assert "power_zone_7" in settings.power_zones
        assert settings.power_zones["power_zone_1"] == (0, 157)

    def test_default_hr_zones_loaded(self):
        """Test that default HR zones are loaded."""
        settings = Settings(fthr=170)

        assert "hr_zone_1" in settings.hr_zone_ranges
        assert "hr_zone_5" in settings.hr_zone_ranges
        # HR Z1 = 0 to int(0.85 * fthr) with fthr=170
        assert settings.hr_zone_ranges["hr_zone_1"] == (0, int(0.85 * 170))

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

        assert settings.ftp == 0  # Default value (unconfigured)
        assert settings.fthr == 0  # Default value (unconfigured)


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


class TestHRZoneThreeTierModel:
    """Test the three-tier HR zone model: LT-based > FTHR % > max-HR %."""

    def test_tier1_lt_based_zones_when_all_provided(self):
        """Tier 1: LT-based zones when lt1_hr + lt2_hr + fthr are all provided."""
        settings = Settings(fthr=170, lt1_hr=129, lt2_hr=155)

        assert settings.hr_zone_ranges["hr_zone_1"] == (0, 129)
        assert settings.hr_zone_ranges["hr_zone_2"] == (129, 155)
        assert settings.hr_zone_ranges["hr_zone_3"] == (155, 170)
        # Z4 upper: fthr + 6 (estimated max_hr when max_hr=0)
        assert settings.hr_zone_ranges["hr_zone_4"][0] == 170
        assert settings.hr_zone_ranges["hr_zone_5"][1] == float("inf")

    def test_tier1_uses_configured_max_hr_for_upper_bound(self):
        """Tier 1: Uses configured max_hr for Z4/Z5 boundary when provided."""
        settings = Settings(fthr=170, lt1_hr=129, lt2_hr=155, max_hr=190)

        # Z4 should go up to the real max_hr, not the estimate
        assert settings.hr_zone_ranges["hr_zone_4"] == (170, 190)
        assert settings.hr_zone_ranges["hr_zone_5"] == (190, float("inf"))

    def test_tier2_coggan_zones_when_only_fthr(self):
        """Tier 2: Coggan %-based zones when only fthr is provided (no LT HR)."""
        settings = Settings(fthr=170)

        # No lt1_hr/lt2_hr → falls through to Coggan %
        assert settings.hr_zone_ranges["hr_zone_1"] == (0, int(0.85 * 170))
        assert settings.hr_zone_ranges["hr_zone_2"] == (
            int(0.85 * 170), int(0.95 * 170)
        )
        assert settings.hr_zone_ranges["hr_zone_5"][1] == float("inf")
        assert len(settings.hr_zone_ranges) == 5

    def test_tier3_max_hr_zones_when_only_max_hr(self):
        """Tier 3: Max-HR %-based zones when only max_hr is provided (no fthr)."""
        settings = Settings(fthr=0, max_hr=190)

        assert settings.hr_zone_ranges["hr_zone_1"] == (0, int(0.60 * 190))
        assert settings.hr_zone_ranges["hr_zone_2"] == (
            int(0.60 * 190), int(0.70 * 190)
        )
        assert settings.hr_zone_ranges["hr_zone_3"] == (
            int(0.70 * 190), int(0.80 * 190)
        )
        assert settings.hr_zone_ranges["hr_zone_4"] == (
            int(0.80 * 190), int(0.90 * 190)
        )
        assert settings.hr_zone_ranges["hr_zone_5"] == (
            int(0.90 * 190), float("inf")
        )

    def test_tier3_zones_not_computed_when_neither_fthr_nor_max_hr(self):
        """No zone computation when both fthr=0 and max_hr=0; zones stay empty."""
        settings = Settings(fthr=0, max_hr=0)

        # With no physiological data configured, zones remain empty
        assert settings.hr_zone_ranges == {}

    def test_tier1_takes_priority_over_tier2(self):
        """Tier 1 (LT-based) takes priority when lt values are provided."""
        settings_lt = Settings(fthr=170, lt1_hr=129, lt2_hr=155)
        settings_coggan = Settings(fthr=170)

        # Z1 upper differs: LT uses lt1_hr=129, Coggan uses 0.85*170=144
        assert settings_lt.hr_zone_ranges["hr_zone_1"][1] == 129
        assert settings_coggan.hr_zone_ranges["hr_zone_1"][1] == int(0.85 * 170)

    def test_tier2_takes_priority_over_tier3(self):
        """Tier 2 (Coggan) takes priority over Tier 3 when fthr > 0."""
        settings_coggan = Settings(fthr=170, max_hr=190)

        # fthr > 0 → Coggan, not max_hr %
        assert settings_coggan.hr_zone_ranges["hr_zone_1"][1] == int(0.85 * 170)
        # NOT int(0.60 * 190)
        assert settings_coggan.hr_zone_ranges["hr_zone_1"][1] != int(0.60 * 190)


class TestEffectiveFthr:
    """Test the effective_fthr property."""

    def test_returns_fthr_when_configured(self):
        """effective_fthr returns fthr when fthr > 0."""
        settings = Settings(fthr=170, max_hr=190)
        assert settings.effective_fthr == 170.0

    def test_estimates_from_max_hr_when_fthr_zero(self):
        """effective_fthr estimates FTHR from max_hr when fthr=0."""
        settings = Settings(fthr=0, max_hr=190)
        expected = round(0.89 * 190, 1)
        assert settings.effective_fthr == expected

    def test_returns_zero_when_neither_configured(self):
        """effective_fthr returns 0 when both fthr=0 and max_hr=0."""
        settings = Settings(fthr=0, max_hr=0)
        assert settings.effective_fthr == 0.0

    def test_fthr_takes_priority_over_max_hr_estimate(self):
        """fthr is always preferred over the max_hr estimate."""
        settings_a = Settings(fthr=165, max_hr=190)
        settings_b = Settings(fthr=0, max_hr=190)

        assert settings_a.effective_fthr == 165.0
        assert settings_b.effective_fthr == round(0.89 * 190, 1)
        assert settings_a.effective_fthr != settings_b.effective_fthr


class TestMaxHrField:
    """Test the max_hr field behaviour."""

    def test_default_max_hr_is_zero(self):
        """max_hr defaults to 0 (not configured)."""
        settings = Settings()
        assert settings.max_hr == 0

    def test_max_hr_can_be_set(self):
        """max_hr can be configured directly."""
        settings = Settings(max_hr=188)
        assert settings.max_hr == 188

    def test_max_hr_loaded_from_yaml(self, temp_config_file):
        """max_hr is read from YAML config."""
        import yaml as _yaml

        config_data = {"fthr": 0, "max_hr": 195, "ftp": 285}
        with open(temp_config_file, "w") as f:
            _yaml.dump(config_data, f)

        settings = load_settings(config_file=temp_config_file)

        assert settings.max_hr == 195
        # Should have used Tier 3 zones
        assert settings.hr_zone_ranges["hr_zone_1"] == (0, int(0.60 * 195))
