# Paper Mill Intelligent Process Control System

**Problem:** During grade changes in paper machines, Basis Weight (target quality metric) frequently goes off-spec (±2.5%), causing waste and lost production. Operators lack predictive guidance before breaches occur.

**Solution:** An intelligent ML-powered layer that:
1. **Predicts risk** of Basis Weight deviation during grade changes
2. **Recommends corrective setpoints** within recipe/actuator constraints
3. **Identifies stabilization drivers** to reduce settling time
4. **Discovers new correlations** between variables not in existing control loops
5. **Provides explainability** with source tagging for every suggestion
6. **Captures operator feedback** for continuous learning

---

## Quick Start

```bash
# Install backend dependencies
pip install -r requirements.txt

# Run synthetic data generator
python backend/data_generator.py

# Start FastAPI server
uvicorn backend.main:app --reload

# In another terminal, start React frontend
cd frontend
npm install
npm start
```

Dashboard will be available at `http://localhost:3000`

---

## Architecture

```
DATA INGESTION
    ↓
FEATURE ENGINEERING & CORRELATION ENGINE
    ↓
PREDICTION MODELS (Risk + Stabilization-Time)
    ↓
RECOMMENDATION ENGINE (with constraint checking)
    ↓
FASTAPI BACKEND
    ↓
REACT DASHBOARD (7 panels)
    ↓
FEEDBACK LOOP (Accept/Reject logging)
```

---

## Directory Structure

```
paper-mill-control/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── data_generator.py       # Synthetic data generator
│   ├── feature_engineering.py  # Feature extraction & correlation engine
│   ├── models.py               # ML model definitions
│   ├── recommender.py          # Recommendation engine
│   ├── database.py             # SQLite setup
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── components/
│   │   │   ├── LiveTrajectory.js
│   │   │   ├── RiskPanel.js
│   │   │   ├── CorrelationDiscovery.js
│   │   │   ├── FutureStateProjection.js
│   │   │   ├── StabilizationDrivers.js
│   │   │   ├── RecommendationFeed.js
│   │   │   └── FeedbackAnalytics.js
│   │   └── index.js
│   ├── package.json
│   └── public/
└── docs/
    ├── ARCHITECTURE.md
    └── PRESENTATION.md
```

---

## Build Status

- [x] Phase 1: Synthetic Data Generator
- [x] Phase 2: Feature Engineering & Correlation Engine
- [x] Phase 3: ML Models (Risk + Stabilization)
- [x] Phase 4: Recommendation Engine
- [X] Phase 5: FastAPI Backend
- [X] Phase 6: React Dashboard
- [X] Phase 7: Integration & Testing
- [X] Phase 8: Documentation & Presentation

---

## Key Features

✅ **Real-time Risk Prediction** – Forecasts Basis Weight deviation probability and time-to-breach  
✅ **Explainable Recommendations** – Every suggestion tagged with inference source  
✅ **Constraint-Safe Setpoints** – Never violates recipe limits or actuator constraints  
✅ **New Correlation Discovery** – Surfaces statistically significant variable relationships  
✅ **Operator Feedback Loop** – Accept/Reject logging for model accuracy tracking  
✅ **Interactive Dashboard** – 7-panel live monitoring and decision support  

---

## Deliverables Checklist

- [ ] Working end-to-end solution on synthetic data
- [ ] Architecture document
- [ ] Dashboard with all 7 required panels
- [ ] Every suggestion source-tagged & explainable
- [ ] Accept/Reject feedback capture & logging
- [ ] Presentation deck

---

**Status:** In active development. See `docs/` for detailed architecture and progress updates.
