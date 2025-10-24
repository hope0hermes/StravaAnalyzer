# Architectural Decision Record: Layered Architecture

## Status
**Accepted** - Implemented in Phase 3

## Context

After Phase 2's metrics refactoring, the codebase still had structural issues:

### Problems
1. **Mixed Concerns**: Data loading, processing, and analysis mixed in single modules
2. **Tight Coupling**: Components directly dependent on implementation details
3. **Complex Pipeline**: 300+ line pipeline class doing everything
4. **Hard to Test**: Monolithic structure made unit testing difficult
5. **Unclear Organization**: No clear place for new features
6. **No Abstraction**: Direct file system dependencies everywhere

### Example of Problems

```python
# Old pipeline.py - 300+ lines
class AnalysisPipeline:
    def process(self):
        # Load data (mixed with other logic)
        df = pd.read_csv(...)  # Direct file access

        # Clean data (mixed)
        df = clean_data(df)

        # Calculate metrics (mixed)
        metrics = calculate_metrics(df)

        # Save results (mixed)
        df.to_csv(...)  # Direct file access

        # All in one place, hard to test or reuse
```

## Decision

We will implement a **layered architecture** with clear separation of concerns:

### Layer Structure

```
┌──────────────────┐
│  SERVICE LAYER   │  ← High-level workflows, orchestration
├──────────────────┤
│  ANALYSIS LAYER  │  ← Business logic, computations
├──────────────────┤
│   DATA LAYER     │  ← Data access, I/O, cleaning
├──────────────────┤
│  METRICS LAYER   │  ← Domain calculations (Phase 2)
└──────────────────┘
```

### Layer Responsibilities

#### 1. Data Layer (`data/`)
**Responsibility**: "How do we get and prepare data?"

- **ActivityDataLoader**: File I/O operations
  - Load activities, streams, thresholds
  - Handle missing files
  - Abstract data source

- **StreamDataProcessor**: Data cleaning & validation
  - Clean and validate stream data
  - Handle missing values
  - Type conversions

- **ActivityRepository**: Query & filtering logic
  - Business queries (by type, recent, etc.)
  - Caching
  - Data filtering

**No Business Logic**: Just data access and cleaning

#### 2. Analysis Layer (`analysis/`)
**Responsibility**: "How do we compute results?"

- **ActivityAnalyzer**: Individual activity analysis
  - Coordinate metrics calculation
  - Activity-type logic
  - Type conversions

- **ActivitySummarizer**: Summaries & aggregations
  - Longitudinal summaries
  - Weekly/monthly aggregations
  - Training load calculations

- **ThresholdEstimator**: Threshold estimation
  - FTP/FTHR estimation
  - Historical trending

**No I/O**: Works with data structures only

#### 3. Service Layer (`services/`)
**Responsibility**: "How do we coordinate workflows?"

- **ActivityService**: Activity workflows
  - Complete activity processing pipeline
  - Coordinate loader + processor + analyzer
  - Error handling and logging

- **AnalysisService**: Analysis orchestration
  - Full analysis workflow
  - Batch processing
  - Results persistence

**No Direct Calculations**: Delegates to analysis layer

#### 4. Metrics Layer (`metrics/`)
**Responsibility**: "How do we calculate specific metrics?"

- Created in Phase 2
- Specialized calculators per domain
- See ADR_001_METRICS_REFACTORING.md

### Design Principles

#### 1. Dependency Rule
**Layers can only depend on layers below them**

```
Services → Analysis → Data → Metrics
    ↓         ↓         ↓
  (can call) (can call) (can call)
```

**Never**: Data layer calling Services
**Never**: Metrics layer calling Analysis

#### 2. Protocol-Based Interfaces

Each layer defines protocols (interfaces):

```python
class DataLoaderProtocol(Protocol):
    def load_activities(self) -> pd.DataFrame: ...

class AnalyzerProtocol(Protocol):
    def analyze(self, activity_row, stream_df) -> dict: ...
```

Benefits:
- Loose coupling
- Easy mocking for tests
- Swappable implementations

#### 3. Composition Over Inheritance

Services compose components:

```python
class ActivityService:
    def __init__(self, settings):
        self.loader = ActivityDataLoader(settings)
        self.processor = StreamDataProcessor(settings)
        self.repository = ActivityRepository(self.loader, settings)
        self.analyzer = ActivityAnalyzer(settings)
```

No deep inheritance hierarchies.

#### 4. Single Responsibility

Each class has ONE job:
- Loader: Load data
- Processor: Clean data
- Repository: Query data
- Analyzer: Analyze data
- Service: Coordinate workflows

#### 5. Dependency Injection

Dependencies passed in constructor:

```python
class ActivityRepository:
    def __init__(self, loader: ActivityDataLoader, settings: Settings):
        self.loader = loader  # Injected
        self.settings = settings
```

Makes testing easy:

```python
def test_repository():
    mock_loader = Mock(spec=ActivityDataLoader)
    repo = ActivityRepository(mock_loader, settings)
    # Test with mock
```

## Alternatives Considered

### Alternative 1: Keep Flat Structure
**Rejected**: Doesn't scale, violates SRP

### Alternative 2: Microservices
**Rejected**: Too complex for current needs, premature optimization

### Alternative 3: Hexagonal Architecture
**Rejected**: Too abstract for this use case, layered is more intuitive

### Alternative 4: MVC Pattern
**Rejected**: We don't have views, layers fit better

## Consequences

### Positive

1. **Clear Organization**: Each layer has obvious purpose
2. **Easy Testing**: Test each layer independently with mocks
3. **Flexibility**: Swap implementations (file → database)
4. **Maintainability**: Find code easily, clear boundaries
5. **Extensibility**: Add features at appropriate layer
6. **Reusability**: Components usable independently
7. **Onboarding**: New developers understand structure quickly

### Negative

1. **More Files**: 11 new modules (acceptable)
2. **Indirection**: More layers to navigate (but clearer)
3. **Initial Complexity**: Takes time to set up (one-time cost)

### Neutral

1. **Learning Curve**: Team needs to understand layering
2. **Over-engineering**: Could be simpler for tiny projects (not our case)

## Implementation Notes

### Phase 3 Scope

- ✅ Create data layer (loader, processor, repository)
- ✅ Create analysis layer (analyzer, summarizer, estimator)
- ✅ Create service layer (activity service, analysis service)
- ✅ Define protocols for each layer
- ✅ Update package exports
- ✅ Create modern pipeline using services
- ✅ Maintain backward compatibility

### Migration Strategy

1. **New code uses new architecture**
2. **Old code remains functional**
3. **Gradual migration** as needed
4. **No breaking changes**

### Testing Strategy

```python
# Data Layer Tests
test_loader.py: Test file I/O
test_processor.py: Test data cleaning
test_repository.py: Test queries (with mock loader)

# Analysis Layer Tests
test_analyzer.py: Test analysis (with mock metrics)
test_summarizer.py: Test summaries
test_estimator.py: Test threshold estimation

# Service Layer Tests
test_activity_service.py: Test workflows (with mocks)
test_analysis_service.py: Test orchestration (with mocks)

# Integration Tests
test_integration.py: Test full pipeline end-to-end
```

## Future Enhancements

### Phase 4+ Possibilities

1. **Dependency Injection Container**
   ```python
   container = DIContainer()
   container.register(ActivityDataLoader)
   service = container.resolve(ActivityService)
   ```

2. **Event System**
   ```python
   # Publish events from layers
   events.publish(ActivityProcessedEvent(activity_id))
   ```

3. **Async Support**
   ```python
   async def process_activity(self, activity_row):
       stream = await self.loader.load_stream_async(...)
   ```

4. **Database Layer**
   ```python
   # Alternative to file loader
   loader = DatabaseActivityLoader(connection_string)
   ```

5. **Caching Layer**
   ```python
   @cached(ttl=3600)
   def get_all_activities(self):
       return self.loader.load_activities()
   ```

## Examples

### Before (Monolithic)

```python
# Everything in one place
class Pipeline:
    def process(self):
        # Load
        df = pd.read_csv("activities.csv")

        # Clean
        df = df.dropna()

        # Calculate
        df['np'] = calculate_np(df)

        # Save
        df.to_csv("enriched.csv")
```

Problems:
- Can't test parts independently
- Can't swap data source
- Can't reuse components
- Hard to modify

### After (Layered)

```python
# Clear separation
# Data Layer
loader = ActivityDataLoader(settings)
processor = StreamDataProcessor(settings)
repository = ActivityRepository(loader, settings)

# Analysis Layer
analyzer = ActivityAnalyzer(settings)

# Service Layer
service = ActivityService(settings)
metrics, stream = service.process_activity(activity_row)
```

Benefits:
- Test each component independently
- Swap loader (file → database)
- Reuse components anywhere
- Clear modification points

## Verification

✅ **Compiles**: Zero errors
✅ **Imports**: All layers import cleanly
✅ **Dependencies**: Unidirectional, no cycles
✅ **Protocols**: All defined and used
✅ **Backward Compatible**: Old code still works

## References

- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Layered Architecture: https://herbertograca.com/2017/08/03/layered-architecture/
- Repository Pattern: https://martinfowler.com/eaaCatalog/repository.html
- Service Layer: https://martinfowler.com/eaaCatalog/serviceLayer.html
- Dependency Injection: https://en.wikipedia.org/wiki/Dependency_injection

## Review

- **Author**: GitHub Copilot
- **Date**: 2025-10-22
- **Reviewers**: N/A (automated implementation)
- **Status**: Implemented and verified
