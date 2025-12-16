# StravaAnalyzer 🚴‍♂️📊

Advanced Python package for analyzing Strava activities with scientific rigor. Get deep insights into training load, performance trends, and physiological adaptations.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-SharedWorkflows-brightgreen)](https://github.com/hope0hermes/SharedWorkflows)

## Table of Contents

- [What It Does](#what-it-does)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Documentation](#documentation)
- [Getting Strava Data](#getting-strava-data)
- [Usage Options](#usage-options)
- [Configuration](#configuration)
- [Testing](#testing)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contact](#contact)

## What It Does

StravaAnalyzer transforms raw Strava data into actionable insights:

- **Dual Metrics**: Every metric calculated for both complete and moving data
- **Time-Weighted Calculations**: Mathematically accurate despite variable sampling and gaps
- **Training Load**: ATL, CTL, TSB, ACWR for injury prevention and optimization
- **Power Analysis**: Normalized Power, IF, TSS, Variability Index, and more
- **Performance Trends**: Longitudinal analysis with rolling averages
- **Zone Distribution**: Training Intensity Distribution (TID) and polarization metrics
- **Scientific Foundation**: Based on Coggan, Friel, and Seiler methodologies

## Quick Start

### Installation

```bash
# Clone
git clone https://github.com/hope0hermes/StravaAnalyzer.git
cd StravaAnalyzer

# Setup environment
uv venv
source .venv/bin/activate

# Install
uv sync
```

### Basic Usage (5 minutes)

**Via CLI (no code required):**
```bash
uv run strava-analyzer run --config config.yaml
```

**Via Python:**
```python
from strava_analyzer.modern_pipeline import ModernPipeline
from strava_analyzer.settings import Settings

pipeline = ModernPipeline(Settings())
pipeline.run()
```

## Key Features

### Per-Activity Metrics
- **Power**: Average, Normalized, Intensity Factor, TSS, Variability Index
- **Efficiency**: Efficiency Factor, aerobic decoupling, fatigue resistance
- **Zones**: 7-zone Coggan model, time-in-zone, Training Intensity Distribution
- **Running**: NGP, rTSS, hrTSS, Functional Threshold Pace
- **All Sports**: HR analysis, elevation, distance

### Power Profile (Rolling 90-Day Window)
- **Critical Power Model**: CP and W' (anaerobic capacity) with R² model fit
- **Anaerobic Energy Index**: AEI = W'/body_weight (J/kg) for power endurance
- **Power Curve**: Maximum mean power at 5s-1hr durations
- **Dynamic Tracking**: CP/W'/AEI update as new peak efforts enter the window

### Longitudinal Analysis
- **Training Load**: ATL (7d fatigue), CTL (42d fitness), TSB (readiness), ACWR (injury risk)
- **Per-Activity Training State**: Each activity has its own CTL/ATL/TSB/ACWR based on time-weighted decay
- **Trends**: Rolling averages, performance curves, zone patterns
- **Estimation**: Dynamic FTP/FTHR from activities

## Documentation

| Doc | Purpose |
|-----|---------|
| [**QUICK_START.md**](docs/QUICK_START.md) | Usage examples (Pipeline, Services, CLI, Custom) |
| [**CONFIGURATION.md**](docs/CONFIGURATION.md) | Configuration options and setup |
| [**METRICS_GUIDE.md**](docs/METRICS_GUIDE.md) | Detailed metric reference |
| [**METRICS.md**](docs/METRICS.md) | Complete metric definitions |
| [**ARCHITECTURE_GUIDE.md**](docs/ARCHITECTURE_GUIDE.md) | System design and layers |
| [**TESTING_STRATEGY.md**](docs/TESTING_STRATEGY.md) | Testing approach |
| [**ADR_001_LAYERED_ARCHITECTURE.md**](docs/ADR_001_LAYERED_ARCHITECTURE.md) | Architecture decisions |
| [**ADR_002_TIME_WEIGHTED_AVERAGING.md**](docs/ADR_002_TIME_WEIGHTED_AVERAGING.md) | Time-weighted accuracy |

## Getting Strava Data

1. Log into Strava account
2. Settings → My Account → Download or Delete Your Account
3. Request data export
4. Extract archive - you need:
   - `activities.csv` (metadata)
   - `Streams/` directory (time-series data)

## Usage Options

### 1. CLI (Simplest)
```bash
uv run strava-analyzer run
uv run strava-analyzer run --config config.yaml --verbose
```
→ See [QUICK_START.md](docs/QUICK_START.md#option-5-command-line-interface)

### 2. Pipeline (Easy)
```python
from strava_analyzer.modern_pipeline import ModernPipeline
pipeline = ModernPipeline(Settings())
pipeline.run()
```
→ See [QUICK_START.md](docs/QUICK_START.md#option-1-pipeline-simplest)

### 3. Services (More Control)
```python
from strava_analyzer.services import AnalysisService
service = AnalysisService(Settings())
enriched_df, summary = service.run_analysis()
```
→ See [QUICK_START.md](docs/QUICK_START.md#option-2-service-based-workflow)

### 4. Components (Custom)
Build workflows with individual components (loaders, processors, analyzers).
→ See [QUICK_START.md](docs/QUICK_START.md#option-4-custom-analysis)

## Configuration

Quick setup with `.env`:
```bash
STRAVA_ANALYZER_FTP=285
STRAVA_ANALYZER_FTHR=170
STRAVA_ANALYZER_RIDER_WEIGHT_KG=70
STRAVA_ANALYZER_ACTIVITIES_FILE=/path/to/activities.csv
STRAVA_ANALYZER_STREAMS_DIR=/path/to/Streams
```

→ See [CONFIGURATION.md](docs/CONFIGURATION.md) for full options

### Input Parameters & Metadata

#### Required Parameters (Athlete Profile)

These parameters define your physiological baseline and are **essential** for all metric calculations:

| Parameter | Type | Range | Description | Used By |
|-----------|------|-------|-------------|---------|
| **ftp** | float | 50-600W | Functional Threshold Power | Power metrics, NP, IF, TSS, zones |
| **fthr** | int | 100-220 bpm | Functional Threshold Heart Rate | HR zones, hrTSS, training load |
| **rider_weight_kg** | float | 30-200 kg | Body weight | Power/kg, Anaerobic Energy Index (W'/kg) |
| **ftpace** | float | 2.5-15 min/km | Functional Threshold Pace (running) | Running pace metrics & zones |

#### Optional Lactate Threshold Parameters

For more accurate zone models, provide lactate threshold values from a ramp test:

| Parameter | Type | Typical Range | Description |
|-----------|------|---------------|-------------|
| **lt1_power** | float | 40-70% FTP | Aerobic Threshold Power |
| **lt2_power** | float | 90-110% FTP | Anaerobic Threshold Power (often = FTP) |
| **lt1_hr** | int | 80-90% FTHR | Aerobic Threshold Heart Rate |
| **lt2_hr** | int | 95-110% FTHR | Anaerobic Threshold Heart Rate |

*When not provided, system defaults to Coggan percentage-based zones.*

#### Training Load Configuration

Control how CTL, ATL, TSB, and ACWR are calculated:

```yaml
training_load:
  ctl_days: 42          # Chronic Training Load window (fitness, typical: 42)
  atl_days: 7           # Acute Training Load window (fatigue, typical: 7)
  ftp_rolling_window_days: 42  # Window for FTP estimation from 20-min efforts
```

#### Power Zone Configuration

Choose between two zone models:

**Coggan Method (default, % of FTP):**
```yaml
power_zones:
  method: "coggan"
  coggan:
    z1: {name: "Active Recovery", lower_percent: 0, upper_percent: 55}
    z2: {name: "Endurance", lower_percent: 55, upper_percent: 75}
    z3: {name: "Tempo", lower_percent: 75, upper_percent: 90}
    z4: {name: "Threshold", lower_percent: 90, upper_percent: 105}
    z5: {name: "VO2 Max", lower_percent: 105, upper_percent: 120}
    z6: {name: "Anaerobic", lower_percent: 120, upper_percent: 150}
    z7: {name: "Sprint", lower_percent: 150, upper_percent: 999}
```

**Lactate Threshold Method (if lt1_power & lt2_power provided):**
```yaml
power_zones:
  method: "lactate"
```

#### Data Paths Configuration

| Parameter | Type | Description |
|-----------|------|-------------|
| **data_dir** | path | Root directory for data files (relative to this is recommended) |
| **activities_file** | path | Path to `activities.csv` from Strava export |
| **streams_dir** | path | Path to `Streams/` directory from Strava export |
| **processed_data_dir** | path | Where to save enriched output files |

#### Processing & Output Configuration

```yaml
verbose: true          # Enable detailed logging
force: true            # Force reprocessing of existing activities
include_power_curve: true  # Compute maximum mean power (MMP) metrics
```

### Output Files

After running analysis, you'll get:

```
processed_data_dir/
├── activities_raw.csv          # Metrics from all data points
├── activities_moving.csv       # Metrics from moving-only data (contiguous time)
├── activity_summary.json       # Longitudinal aggregates & trends
└── power_curve_activities.csv  # MMP values across durations (optional)
```

**Key columns in output:**
- `moving_time`: Elapsed time while moving (seconds)
- `distance`: Total distance (km)
- `elevation_gain`: Total elevation (m)
- `average_power`: Time-weighted average watts
- `normalized_power`: Weighted power with 30-sec rolling average
- `training_stress_score`: Workout intensity × duration (TSS)
- `intensity_factor`: NP / FTP (IF)
- `efficiency_factor`: NP / HR (EF)
- `power_per_kg`: Average power normalized to body weight
- Zone distribution metrics (`power_tid_z1_percentage`, etc.)
- Training load (`chronic_training_load`, `acute_training_load`, `training_stress_balance`)
- CP model (`critical_power`, `anaerobic_capacity_joules`, `model_r_squared`)

## Testing

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=strava_analyzer

# Specific file
uv run pytest tests/test_metrics.py
```

## Architecture

Layered design for maintainability:

```
CLI / Pipeline (User entry)
    ↓
Service Layer (Workflows)
    ↓
Analysis Layer (Business logic)
    ↓
Data Layer (I/O & prep)
    ↓
Metrics Layer (Calculations)
```

→ See [ARCHITECTURE_GUIDE.md](docs/ARCHITECTURE_GUIDE.md) for details

## Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feat/your-feature`
3. Make changes & test: `uv run pytest`
4. Lint: `uv run ruff check .`
5. Commit (conventional): `git commit -m 'feat: description'`
6. Push and open PR

**Code Quality:**
```bash
uv run pytest && uv run ruff check . && uv run mypy src/strava_analyzer
```

## Roadmap

- [ ] Web Dashboard (Plotly/Dash)
- [ ] Real-time API integration
- [ ] ML: FTP progression prediction
- [ ] Multi-sport support
- [ ] Advanced CP modeling
- [ ] Comparative analysis

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- **Dr. Andrew Coggan**: Power metrics, zones, TSS
- **Joe Friel**: TSB, periodization
- **Dr. Stephen Seiler**: Polarized training
- **Allen & Coggan**: "Training and Racing with a Power Meter"

## Contact

- **Author**: Israel Barragan
- **GitHub**: [@hope0hermes](https://github.com/hope0hermes)
- **Issues**: [GitHub Issues](https://github.com/hope0hermes/StravaAnalyzer/issues)

---

**Built for athletes, coaches, and data enthusiasts.**

If you find this useful, please star ⭐ on [GitHub](https://github.com/hope0hermes/StravaAnalyzer)!

**Happy Analyzing! 🚴‍♂️📈**

