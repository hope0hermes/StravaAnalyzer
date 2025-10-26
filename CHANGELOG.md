# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.4] - 2025-10-26

### Changed
- fix: skip tests on version bump commits to reduce CI waste (fc21142)


## [1.0.3] - 2025-10-26

### Changed
- fix: detect version bumps from release branch merges (3c9fbeb)


## [1.0.2] - 2025-10-26

### Changed
- fix: prevent infinite loop by detecting release PR merges (0c0e1be)
- chore: trigger CI checks (8b254a1)
- chore: bump version to 1.0.1 (446fc7f)
- chore: trigger CI checks (62c1a38)
- fix: update release workflows to PR-based approach (ef66dbc)


## [1.0.1] - 2025-10-26

### Changed
- chore: trigger CI checks (62c1a38)
- fix: update release workflows to PR-based approach (ef66dbc)


## [1.0.0] - 2025-10-24

### Added

#### Architecture
- Layered architecture with clear separation of concerns (ADR-001)
- Data layer: loaders, processors, and repositories for data management
- Metrics layer: calculators for power, heart rate, efficiency, fatigue, and TID
- Analysis layer: analyzers, summarizers, and threshold estimators
- Service layer: high-level business logic orchestration
- Presentation layer: CLI and pipeline components

#### Metrics & Analysis
- Time-weighted averaging for accurate cycling metrics (ADR-002)
- Comprehensive power metrics:
  - Average and normalized power (NP)
  - Intensity Factor (IF)
  - Training Stress Score (TSS)
  - Variability Index (VI)
  - Power curves and Critical Power (CP) modeling
- Heart rate analysis:
  - Zone-based calculations
  - Heart rate Training Stress Score (hrTSS)
  - Heart rate reserve calculations
- Training load management:
  - Chronic Training Load (CTL) - 28-day fitness
  - Acute Training Load (ATL) - 7-day fatigue
  - Training Stress Balance (TSB) - freshness indicator
  - Acute:Chronic Workload Ratio (ACWR)
- Advanced metrics:
  - Fatigue resistance analysis
  - Rolling efficiency (Pw:Hr and EF)
  - Training Intensity Distribution (TID) - polarization analysis
- Zone distribution analysis for power, HR, pace, cadence, and gradient

#### Configuration
- Pydantic-based settings with type validation
- YAML configuration file support
- Environment variable overrides with `STRAVA_ANALYZER_` prefix
- Comprehensive zone definitions (power, HR, pace, cadence, slope)
- Athlete-specific parameters (FTP, FTHR, weight)
- Configurable power curve intervals

#### CLI Commands
- `strava-analyzer process`: Execute full pipeline with enriched activity output
- `strava-analyzer summarize`: Generate comprehensive activity summaries
- `strava-analyzer analyze`: Analyze individual activities
- `strava-analyzer estimate-thresholds`: Estimate FTP and FTHR from activity data
- Rich logging and error handling
- JSON and CSV output formats

#### Testing
- 71 unit tests with pytest
- 38% overall test coverage (88% on power metrics, 97% on base calculators)
- Comprehensive test fixtures for realistic scenarios
- pytest-cov integration for coverage reporting

#### Documentation
- Architecture Decision Records (ADRs):
  - ADR-001: Layered Architecture
  - ADR-002: Time-Weighted Averaging
- Comprehensive architecture guide
- Detailed metrics documentation
- Testing strategy guide
- Example configurations and sample data
- Interactive Jupyter dashboard for data visualization

#### Development Tools
- Hatch-based project management
- Ruff for fast linting and formatting
- MyPy for static type checking
- Pylint for code quality analysis
- GitHub Actions CI/CD workflow for automated testing
- Support for Python 3.10, 3.11, and 3.12

### Technical Details

**Core Dependencies:**
- pandas >=2.0.0, numpy >=1.20.0 for data processing
- pydantic ~2.11.7 & pydantic-settings ~2.10.1 for configuration
- click >=8.0.0 for CLI interface
- scipy >=1.7.0 for advanced calculations
- PyYAML >=6.0.1 for configuration files

**Package Structure:**
```
src/strava_analyzer/
├── analysis/         # High-level analysis logic
├── data/            # Data loading and processing
├── metrics/         # Metric calculators
├── services/        # Service layer
├── cli.py           # Command-line interface
├── pipeline.py      # Data processing pipeline
├── models.py        # Pydantic data models
├── settings.py      # Configuration management
├── constants.py     # Constants and thresholds
└── exceptions.py    # Custom exceptions
```

[1.0.0]: https://github.com/hope0hermes/StravaAnalyzer/releases/tag/v1.0.0
