# StravaAnalyzer Examples

This directory contains example files to help you get started with StravaAnalyzer.

## Files

### `config_example.yaml`
Example configuration file showing all available settings:
- **Data paths**: Where to find your Strava data
- **Athlete settings**: FTP, FTHR, weight, max heart rate
- **Power zones**: 7-zone model configuration
- **Heart rate zones**: 5-zone model configuration
- **Analysis parameters**: TID zones, smoothing windows, etc.

**Usage:**
1. Copy this file to your project root: `cp examples/config_example.yaml config.yaml`
2. Edit `config.yaml` with your personal settings (FTP, FTHR, weight, etc.)
3. Update paths to point to your Strava data directory
4. Run StravaAnalyzer with your configuration

### `enriched_activities_sample.csv`
Sample output from the StravaAnalyzer pipeline showing enriched activity data with all calculated metrics.

**What's included:**
- Base activity data (distance, time, elevation)
- Power metrics (average, normalized, TSS, IF, VI)
- Heart rate metrics (average, max, hrTSS)
- Efficiency metrics (EF, decoupling, first/second half comparison)
- **TID metrics** (polarization index, zone distribution, TDR)
- **Fatigue metrics** (fatigue index, power sustainability)
- Power and HR zone time distributions

**Usage:**
- Use this as a reference for the expected output format
- Test dashboard notebooks with this sample data
- Understand the metrics before running on your full dataset

## Quick Start

1. **Set up configuration:**
   ```bash
   cp examples/config_example.yaml config.yaml
   # Edit config.yaml with your settings
   ```

2. **Run the pipeline:**
   ```bash
   strava-analyzer run --config config.yaml
   ```

3. **Explore results:**
   ```bash
   jupyter notebook notebooks/strava_dashboard.ipynb
   ```

## Configuration Tips

### Setting Your FTP
Your Functional Threshold Power (FTP) is critical for accurate power zone calculations:
- Use your most recent 20-minute or ramp test result
- Update regularly (every 6-8 weeks during training)
- Default zones are based on Andrew Coggan's 7-zone model

### Setting Your FTHR
Functional Threshold Heart Rate (FTHR):
- Typically 90-95% of max heart rate for well-trained athletes
- Can be determined from a 20-minute all-out effort (average HR)
- Update if your fitness changes significantly

### Data Paths
Point to where you've downloaded your Strava data:
- `data_dir`: Your `activities.csv` and `Streams/` directory
- `processed_data_dir`: Where enriched results will be saved

## Need Help?

See the main [README.md](../README.md) for comprehensive documentation and troubleshooting.
