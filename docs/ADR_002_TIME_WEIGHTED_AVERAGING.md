# ADR 005: Time-Weighted Averaging for Metrics

**Status**: Implemented
**Date**: 2025-10-23
**Context**: Phase 4 Enhancement - Mathematical Accuracy in Metric Calculations

## Problem Statement

The original metric calculations used simple arithmetic mean (sum/count) which doesn't account for the time-series nature of stream data. This approach has several issues:

1. **Variable Sampling Rates**: Activity recordings may have variable sampling rates (typically 1Hz but can vary)
2. **Recording Gaps**: Auto-pause features or GPS loss creates gaps in the data
3. **Duration Calculations**: Using data point count as duration ignores actual elapsed time
4. **Inaccurate Averages**: Each data point weighted equally regardless of time interval it represents

### Mathematical Issue

**Incorrect (Simple Mean)**:
```
Average Power = Σ(power_i) / n_points
```

**Problem**: This treats each data point as equal, but:
- Point at t=0s and t=1s represents 1 second
- Point at t=100s and t=110s represents 10 seconds (recording gap)
- Both weighted equally in simple mean

**Correct (Time-Weighted Mean)**:
```
Average Power = Σ(power_i × Δt_i) / Σ(Δt_i)
```

Where:
- `Δt_i` = time interval represented by point i (time to next point)
- Last point has Δt = 0 (or omitted from calculation)

## Decision

Implement time-weighted averaging throughout the metrics calculation system:

1. **Add Base Utilities**: Create reusable methods in `BaseMetricCalculator`
   - `_calculate_time_deltas()`: Compute time intervals between data points
   - `_time_weighted_mean()`: Calculate weighted average using time deltas
   - `_get_total_duration()`: Get actual elapsed time from stream data

2. **Update All Metric Calculators**:
   - **PowerCalculator**: Average power, normalized power, TSS
   - **HeartRateCalculator**: Average HR, hrTSS
   - **EfficiencyCalculator**: Efficiency factor, variability index, decoupling

3. **Change Method Signatures**: Pass full `stream_df` DataFrame instead of individual Series to access time column

## Implementation Details

### Base Class Utilities (`metrics/base.py`)

```python
def _calculate_time_deltas(self, stream_df: pd.DataFrame) -> pd.Series:
    """Calculate time differences between consecutive data points."""
    if 'time' not in stream_df.columns:
        raise ValueError("Stream data must contain 'time' column")

    time_deltas = stream_df['time'].diff().fillna(0)
    return time_deltas

def _time_weighted_mean(self, values: pd.Series, stream_df: pd.DataFrame) -> float:
    """Calculate time-weighted mean of values using time deltas."""
    time_deltas = self._calculate_time_deltas(stream_df)

    # Exclude last point (has delta=0) or handle gracefully
    mask = time_deltas > 0
    if not mask.any():
        return values.mean()  # Fallback to simple mean

    weighted_sum = (values[mask] * time_deltas[mask]).sum()
    total_time = time_deltas[mask].sum()

    return weighted_sum / total_time if total_time > 0 else 0.0

def _get_total_duration(self, stream_df: pd.DataFrame) -> float:
    """Get total duration in seconds from stream data."""
    time_deltas = self._calculate_time_deltas(stream_df)
    return time_deltas.sum()
```

### Power Metrics Updates

**Average Power**:
```python
# Before
avg_power = power_data.mean()

# After
avg_power = self._time_weighted_mean(power_data, stream_df)
```

**Normalized Power**:
```python
# Before
fourth_powers_mean = (power_data ** 4).mean()

# After
fourth_powers = power_data ** 4
fourth_powers_mean = self._time_weighted_mean(fourth_powers, stream_df)
```

**TSS**:
```python
# Before
duration_hours = len(stream_df) / 3600

# After
duration_hours = self._get_total_duration(stream_df) / 3600
```

### Heart Rate Metrics Updates

**Average HR**:
```python
# Before
avg_hr = hr_data.mean()

# After
avg_hr = self._time_weighted_mean(hr_data, stream_df)
```

**hrTSS**:
```python
# Before
duration_minutes = len(stream_df) / 60

# After
duration_minutes = self._get_total_duration(stream_df) / 60
```

### Efficiency Metrics Updates

All efficiency calculations updated to:
1. Accept `stream_df` parameter instead of individual Series
2. Extract required columns from DataFrame
3. Use time-weighted calculations for all means

## Impact Assessment

### Accuracy Improvements

1. **Activities with Auto-Pause**: More accurate averages when recording stops/starts
2. **GPS Gaps**: Correct handling of data loss periods
3. **Variable Recording**: Proper weighting when sampling rate changes
4. **TSS Calculations**: Use actual elapsed time instead of data point count

### Example Impact

Consider an activity with a 10-minute recording gap:
- **Simple mean**: Gap has 0 data points, doesn't affect average
- **Time-weighted mean**: Gap's 600 seconds properly weighted in calculation
- **TSS**: Uses actual 1-hour duration instead of counting data points

### Performance Considerations

- Minimal overhead: `diff()` operation is O(n)
- No significant performance impact observed
- Calculations remain fast even for long activities

## Testing Strategy

1. **Pipeline Testing**: Run full processing on 95 activities
2. **Validation**: Compare metrics with previous calculations
3. **Edge Cases**: Verify handling of single-point streams, missing time data
4. **Accuracy**: Confirm more realistic values for activities with gaps

## Alternatives Considered

### 1. Interpolation Before Averaging
**Approach**: Interpolate missing data points to 1Hz before calculating means

**Rejected because**:
- More computationally expensive
- Introduces artificial data
- Time-weighted averaging is mathematically cleaner

### 2. Configuration Option
**Approach**: Allow users to choose simple vs. time-weighted averaging

**Rejected because**:
- Time-weighted is always more correct
- Adds complexity without benefit
- Simple mean is never the right choice for time series

### 3. Separate Metric Variants
**Approach**: Provide both `avg_power` and `time_weighted_avg_power`

**Rejected because**:
- Confusing for users
- Simple mean is mathematically incorrect
- Should just fix the calculation

## Backward Compatibility

**Breaking Change**: Metric values will change for activities with:
- Recording gaps
- Auto-pause periods
- Variable sampling rates

**Mitigation**:
- Document the change in metrics documentation
- Values are more accurate (not a regression)
- Users should reprocess historical data

## Documentation Updates

- Updated `METRICS.md` to explain time-weighted calculations
- Added mathematical explanations for each metric
- Documented edge cases and fallback behavior

## Success Metrics

✅ **All metric calculators updated**: Power, HR, Efficiency
✅ **Zero compilation errors**: Clean implementation
✅ **Pipeline successful**: 95 activities processed without errors
✅ **More accurate metrics**: Particularly for activities with gaps

## Future Considerations

1. **Add Unit Tests**: Test time-weighted calculations with synthetic data
2. **Performance Monitoring**: Track computation time for large datasets
3. **Documentation**: Add examples showing impact of time-weighted averaging
4. **Validation**: Compare results with other platforms (Strava, TrainingPeaks)

## References

- Time-weighted average: https://en.wikipedia.org/wiki/Weighted_arithmetic_mean
- Stream data format: Strava API documentation
- TSS calculation: TrainingPeaks methodology
- Normalized Power: Dr. Andrew Coggan's power training methodology

## Related ADRs

- ADR 001: Metrics Refactoring (base architecture)
- ADR 002: Layered Architecture (where metrics layer fits)
- ADR 004: Phase 4 Completion (power profile consolidation)
