# Paper Mill Intelligent Process Control System
## Hackathon Solution - Complete Build Guide

### Quick Start

```bash
# Make setup script executable
chmod +x setup.sh

# Run complete setup
./setup.sh
```

Then start in two terminals:

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend Dashboard:**
```bash
cd frontend
npm start
```

Access dashboard at: http://localhost:3000

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION LAYER                        │
│  (QCS history / DCS historian / MIS reports / operator logs)     │
│  ► Synthetic data generator: 200 grade-change events             │
│  ► Historian: stock_flow, filler_flow, steam_pressure, etc      │
│  ► Operator actions & alarms logged                              │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            FEATURE ENGINEERING & CORRELATION ENGINE              │
│  ► Rolling statistics (mean, std, min, max over time windows)   │
│  ► Rate-of-change features (velocity, acceleration)             │
│  ► Cross-correlation lag detection between variables             │
│  ► Mutual information + Pearson correlation scoring              │
│  ► Known vs. novel correlation classification                    │
│  ► Surfaces NEW relationships NOT in existing MPC loops          │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               PREDICTION ENGINE (2 models)                       │
│  ► Model 1: Deviation-Risk Classifier (Gradient Boosting)        │
│    - Input: Feature vector from event data                       │
│    - Output: P(Basis Weight breach ±2.5%)                       │
│    - Feature importance ranking                                  │
│                                                                  │
│  ► Model 2: Stabilization-Time Regressor (Gradient Boosting)    │
│    - Input: Feature vector                                       │
│    - Output: Predicted time-to-settle (seconds)                 │
│    - Variable importance (which loops drive slow settling)       │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           RECOMMENDATION & RATIONALE ENGINE                      │
│  ► Risk Mitigation: Suggest conservative setpoints if high risk  │
│  ► Stabilization: Aggressive ramps for slow-settling events      │
│  ► Correlation-Based: Fine-tune novel correlated variables       │
│  ► Constraint Checking: All recommendations respect recipe       │
│  ► Source Tagging: 6 sources (historical_data, recipe_constraint,│
│    correlation_model, operator_pattern, stabilization_driver,    │
│    risk_mitigation)                                              │
│  ► Confidence Scoring: 0-1 based on prediction uncertainty       │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (13 endpoints)                │
│  GET  /health                 - Health check                     │
│  GET  /events                 - List recent grade changes        │
│  POST /predict-risk           - Breach probability forecast      │
│  POST /predict-stabilization  - Settling time prediction         │
│  GET  /trajectory/{event_id}  - Full time-series data            │
│  POST /recommend-setpoints    - Generate recommendations         │
│  GET  /correlations           - Discovered relationships         │
│  POST /feedback               - Log operator Accept/Reject       │
│  GET  /feedback-analytics     - Acceptance rate & accuracy       │
│  POST /initialize-data        - Generate synthetic data          │
│  GET  /stats                  - System-wide statistics           │
└───────────────────────────┬───────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REACT DASHBOARD (7 PANELS)                    │
│  1. Live Trajectory Panel                                        │
│     ► Actual vs. target vs. ±2.5% band                          │
│     ► Real-time line chart                                       │
│                                                                  │
│  2. Risk Panel                                                   │
│     ► Risk probability gauge                                     │
│     ► Top risk drivers (bar chart)                              │
│     ► Will/won't breach indicator                                │
│                                                                  │
│  3. Correlation Discovery Panel                                  │
│     ► Novel correlations (not in known MPC loops)               │
│     ► Strength heatmap                                           │
│     ► Impact on Basis Weight                                     │
│                                                                  │
│  4. Future-State Projection Panel                                │
│     ► Trend analysis & forecasting                               │
│     ► If current trend continues...                              │
│     ► Stability assessment                                       │
│                                                                  │
│  5. Stabilization Drivers Panel                                  │
│     ► Variables affecting settling time                          │
│     ► Top factors ranked by impact                               │
│     ► Suggested ramp adjustments                                 │
│                                                                  │
│  6. Recommendation Feed Panel                                    │
│     ► Ranked suggestions by confidence                           │
│     ► Variable, current value, recommended value                 │
│     ► Expected effect + source tag                               │
│     ► Accept/Reject buttons (human-in-the-loop)                 │
│     ► Rationale text (grounded in numeric evidence)              │
│                                                                  │
│  7. Feedback Analytics Panel                                     │
│     ► Operator acceptance rate (%)                               │
│     ► Grade change success rate                                  │
│     ► Average deviation & settling time                          │
│     ► Historical trends & insights                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Breakdown

### Backend Modules

#### `database.py`
- **Purpose**: SQLite schema initialization
- **Tables**:
  - `grade_changes` – Event metadata + outcomes
  - `historian` – Time-series data (5s resolution)
  - `operator_actions` – Manual interventions
  - `alarms` – Diagnostic events
  - `recommendations` – Suggested setpoints + feedback
  - `correlations` – Discovered variable relationships

#### `data_generator.py`
- **Purpose**: Synthetic realistic grade-change data
- **Generates**: 200 events with:
  - Phase 1: Ramp (30%)
  - Phase 2: Transient/overshoot (40%)
  - Phase 3: Stabilization/decay (30%)
  - Realistic lags (filler→BW, steam→moisture)
  - 30% off-spec rate (failure cases)
  - Noise + realistic constraints

#### `feature_engineering.py`
- **Classes**: `FeatureEngineer`, `CorrelationEngine`
- **Features Extracted**:
  - Rolling statistics (mean, std, min, max)
  - Rate-of-change (velocity, acceleration, skew)
  - Lag detection (cross-correlation)
  - Initial, final, change, volatility per variable
- **Correlation Methods**:
  - Pearson correlation + p-value
  - Spearman rank correlation
  - Mutual information (discretized bins)
  - Known vs. novel classification
  - Impact on Basis Weight quantification

#### `models.py`
- **Class 1**: `DeviationRiskModel`
  - Algorithm: Gradient Boosting Classifier
  - Input: Feature vector
  - Output: P(breach), top risk drivers (feature importance)
  - Train/test split: 80/20 with stratification
  - Saves: Model, scaler, feature names

- **Class 2**: `StabilizationTimeModel`
  - Algorithm: Gradient Boosting Regressor
  - Input: Feature vector
  - Output: Predicted settling time (seconds)
  - Saves: Model, scaler, stabilization drivers (feature importance)

#### `recommender.py`
- **Class**: `RecommendationEngine`
- **Strategies** (4 types):
  1. **Risk Mitigation** – If high breach risk, suggest conservative ramps
  2. **Stabilization** – If settling is slow, suggest aggressive ramps
  3. **Correlation-Based** – Fine-tune novel correlated variables
  4. **Operator Pattern** – (Optional) Learn from past interventions
- **Constraint Checking**: All setpoints checked against recipe limits
- **Source Tagging**: Each recommendation tagged with inference source
- **Outputs**: Recommended value, expected effect, rationale, confidence

#### `main.py` (FastAPI)
- **13 Endpoints** (see API section below)
- **Middleware**: CORS enabled for frontend
- **Error Handling**: Try/catch with HTTP exceptions

### Frontend Components

All React components:
- Call FastAPI `/` endpoints via axios
- Render with Recharts (line, bar, pie charts)
- Responsive design (mobile-friendly)
- Dark theme (professional)

1. **LiveTrajectory.js** – Line chart: Actual vs. Target vs. Band
2. **RiskPanel.js** – Risk gauge + bar chart of drivers
3. **CorrelationDiscovery.js** – Novel correlations with strength bars
4. **FutureStateProjection.js** – Trend forecast line chart
5. **StabilizationDrivers.js** – Settling time + top factors bar chart
6. **RecommendationFeed.js** – List of ranked suggestions with feedback
7. **FeedbackAnalytics.js** – Pie charts + analytics

---

## API Endpoints

### Health & Data Management
- `GET /health` – Returns `{"status": "ok"}`
- `POST /initialize-data?num_events=200` – Generate synthetic data + train models
- `GET /stats` – System-wide statistics (outcomes, avg deviation, settling time)

### Event & Trajectory
- `GET /events?limit=20` – List recent grade changes
- `GET /trajectory/{event_id}` – Full time-series + metadata

### Predictions
- `POST /predict-risk` – Body: `{"event_id": "..."}` → Risk probability + drivers
- `POST /predict-stabilization` – Body: `{"event_id": "..."}` → Settling time + factors

### Recommendations & Correlations
- `POST /recommend-setpoints` – Body: `{"event_id": "..."}` → Ranked recommendations
- `GET /correlations?event_id=...&min_threshold=0.4` – Novel correlations

### Feedback Loop
- `POST /feedback` – Body: `{"event_id": "...", "rec_id": 1, "accepted": true, "outcome": "..."}` → Log feedback
- `GET /feedback-analytics` – Acceptance rate, accuracy metrics

---

## Data Flow

### Live Grade Change Scenario
1. **User selects event** from sidebar in React dashboard
2. **LiveTrajectory panel** fetches `/trajectory/{event_id}` → Displays historical data
3. **RiskPanel** calls `POST /predict-risk` → Returns probability + top drivers
4. **StabilizationDrivers** calls `POST /predict-stabilization` → Returns settling time + factors
5. **CorrelationDiscovery** calls `GET /correlations` → Returns novel relationships
6. **FutureStateProjection** analyzes recent trend → Projects forward
7. **RecommendationFeed** calls `POST /recommend-setpoints` → Returns ranked suggestions with:
   - Variable name, current value, recommended value
   - Expected effect (plain English)
   - Source tag (e.g., "risk_mitigation")
   - Rationale (grounded in numeric evidence)
   - Confidence score (0-1)
8. **Operator reviews** and clicks Accept or Reject
9. **Accept/Reject logged** via `POST /feedback`
10. **FeedbackAnalytics** aggregates acceptance rate for model improvement

---

## Key Design Decisions

### 1. Synthetic Data
- **Why**: No real QCS data available; synthetic data lets us test end-to-end
- **Realism**: 3-phase transitions (ramp, transient, stabilization) with realistic lag/interaction effects
- **Failure Rate**: 30% off-spec to simulate real variability

### 2. Gradient Boosting Models
- **Why**: Non-linear, handles feature interactions well, provides feature importance
- **Alternative**: Could use LSTM for time-series, but GB is faster to train/explain

### 3. Source Tagging
- **Why**: Every recommendation must be traceable; operators need to understand why
- **Tags**: historical_data, recipe_constraint, correlation_model, operator_pattern, stabilization_driver, risk_mitigation

### 4. Human-in-the-Loop Feedback
- **Why**: Operators know the mill better than the model; feedback improves trust & accuracy
- **Implementation**: Accept/Reject buttons logged in DB for future retraining

### 5. Constraint Checking
- **Why**: Never recommend out-of-bounds setpoints (QCS safety requirement)
- **Implementation**: Recipe limits fetched from DB, values constrained before return

---

## Deployment

### Development
```bash
./setup.sh  # Generates data, trains models
cd backend && uvicorn main:app --reload
cd frontend && npm start
```

### Production
```bash
# Backend
gunicorn -w 4 backend.main:app

# Frontend
npm run build  # Creates optimized bundle
npm install -g serve
serve -s build
```

### Docker (Optional)
```dockerfile
FROM python:3.11
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

---

## Testing

### Synthetic Data Validation
```bash
python3 backend/data_generator.py
# Checks: 200 events created, realistic trajectories, outcome labels assigned
```

### Feature Extraction
```bash
python3 backend/feature_engineering.py
# Checks: Features extracted, correlations discovered, stored in DB
```

### Model Training
```bash
python3 backend/models.py
# Checks: Both models train, accuracy > 60%, features ranked
```

### Recommendation Engine
```bash
python3 backend/recommender.py
# Checks: Recommendations generated, all within constraints, source tags assigned
```

### API Tests (Manual)
```bash
curl http://localhost:8000/health
curl http://localhost:8000/events?limit=5
curl -X POST http://localhost:8000/predict-risk -d '{"event_id": "GC_1001"}'
```

---

## Future Enhancements

1. **LSTM/RNN Models** – For better time-series predictions during active transitions
2. **Online Learning** – Retrain models incrementally as new feedback arrives
3. **Explainability (SHAP)** – Show individual feature contributions to predictions
4. **Alarm Integration** – Real-time alarm data ingest from QCS
5. **Multi-Grade Optimization** – Suggest grade sequence to minimize off-spec
6. **Anomaly Detection** – Flag unusual process behaviors
7. **Mobile App** – iOS/Android native app for mill floor access
8. **Historical Analysis** – Drill down into past events + what-if scenarios

---

## Known Limitations

1. **Synthetic Data** – Not representative of your specific mill; retrain on real data
2. **No Real QCS Integration** – Would need QCS API/historian connection
3. **Single-Variable Optimization** – Each variable recommended independently (not jointly optimized)
4. **No Feedback Retraining** – Operator feedback not yet fed back to retrain models
5. **Limited Domain Knowledge** – No physics-based constraints (e.g., heat balance equations)

---

## Support & Questions

For issues or questions:
1. Check API docs: http://localhost:8000/docs
2. Review synthetic data: `backend/data/control_system.db`
3. Check model artifacts: `backend/models/`
4. Browser console for frontend errors

---

**Status**: Ready for hackathon presentation. All deliverables complete.
