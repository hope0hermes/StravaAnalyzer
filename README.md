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

### Longitudinal Analysis
- **Training Load**: ATL (7d fatigue), CTL (42d fitness), TSB (readiness), ACWR (injury risk)
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

