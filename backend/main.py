"""FastAPI backend for paper mill control system."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import time
from database import init_db, get_connection
from data_generator import SyntheticGradeChangeGenerator
from feature_engineering import FeatureEngineer, CorrelationEngine
from models import DeviationRiskModel, StabilizationTimeModel, train_all_models
from recommender import RecommendationEngine, get_feedback_analytics

# Initialize database
init_db()

app = FastAPI(
    title="Paper Mill Intelligent Process Control",
    description="ML-powered grade change risk prediction and recommendation engine",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class PredictionRequest(BaseModel):
    event_id: str

class FeedbackRequest(BaseModel):
    event_id: str
    rec_id: int
    accepted: bool
    outcome: Optional[str] = None

class TrajectoryPoint(BaseModel):
    timestamp: float
    stock_flow: float
    filler_flow: float
    steam_pressure: float
    machine_speed: float
    basis_weight: float
    moisture: float
    ash: float
    caliper: float

# Endpoints

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Paper Mill Control System"}

@app.get("/events")
def get_events(limit: int = 20):
    """Get list of recent grade change events."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT event_id, from_grade, to_grade, timestamp_start, outcome_label, max_deviation_pct
            FROM grade_changes
            ORDER BY timestamp_start DESC
            LIMIT ?
        """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "event_id": row[0],
                "from_grade": row[1],
                "to_grade": row[2],
                "timestamp": row[3],
                "outcome": row[4],
                "max_deviation_pct": row[5],
            })
        
        conn.close()
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict-risk")
def predict_risk(request: PredictionRequest):
    """Predict Basis Weight deviation risk for an event."""
    try:
        conn = get_connection()
        fe = FeatureEngineer(conn)
        
        # Extract features
        features = fe.extract_all_features(request.event_id)
        if not features:
            raise ValueError("No features extracted for event")
        
        # Get risk prediction
        drm = DeviationRiskModel()
        drm.load()
        risk_result = drm.predict_risk(features)
        
        conn.close()
        return risk_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict-stabilization")
def predict_stabilization(request: PredictionRequest):
    """Predict time-to-stabilize for an event."""
    try:
        conn = get_connection()
        fe = FeatureEngineer(conn)
        
        # Extract features
        features = fe.extract_all_features(request.event_id)
        if not features:
            raise ValueError("No features extracted for event")
        
        # Get stabilization prediction
        stm = StabilizationTimeModel()
        stm.load()
        stab_result = stm.predict_stabilization_time(features)
        
        conn.close()
        return stab_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trajectory/{event_id}")
def get_trajectory(event_id: str):
    """Get time-series trajectory for an event."""
    try:
        conn = get_connection()
        fe = FeatureEngineer(conn)
        df = fe.get_event_data(event_id)
        
        if df.empty:
            raise ValueError(f"No data for event {event_id}")
        
        # Get grade change info
        cursor = conn.cursor()
        cursor.execute("""
            SELECT recipe_target_basis_weight, outcome_label
            FROM grade_changes
            WHERE event_id = ?
        """, (event_id,))
        grade_info = cursor.fetchone()
        
        # Convert to list of points
        trajectory = []
        for _, row in df.iterrows():
            trajectory.append({
                "timestamp": row["timestamp"],
                "stock_flow": float(row["stock_flow"]),
                "filler_flow": float(row["filler_flow"]),
                "steam_pressure": float(row["steam_pressure"]),
                "machine_speed": float(row["machine_speed"]),
                "basis_weight": float(row["basis_weight"]),
                "moisture": float(row["moisture"]),
                "ash": float(row["ash"]),
                "caliper": float(row["caliper"]),
            })
        
        conn.close()
        
        return {
            "event_id": event_id,
            "target_basis_weight": grade_info[0],
            "outcome": grade_info[1],
            "trajectory": trajectory,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend-setpoints")
def recommend_setpoints(request: PredictionRequest):
    """Generate setpoint recommendations for an event."""
    try:
        conn = get_connection()
        re = RecommendationEngine(conn)
        
        recommendations = re.generate_recommendations(request.event_id)
        
        # Store recommendations in database
        cursor = conn.cursor()
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendations
                (event_id, timestamp, variable, recommended_value, expected_effect, source_tag, rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                request.event_id,
                time.time(),
                rec["variable"],
                rec["recommended_value"],
                rec["expected_effect"],
                rec["source_tag"],
                rec["rationale"],
            ))
        conn.commit()
        
        conn.close()
        
        return {
            "event_id": request.event_id,
            "recommendations": recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/correlations")
def get_correlations(event_id: str = None, min_threshold: float = 0.4):
    """Get discovered correlations."""
    try:
        conn = get_connection()
        ce = CorrelationEngine(conn)
        
        if event_id:
            correlations = ce.discover_correlations_for_event(event_id, min_threshold)
        else:
            correlations = ce.get_new_correlations(min_threshold)
        
        conn.close()
        return {"correlations": correlations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    """Submit operator feedback on a recommendation."""
    try:
        conn = get_connection()
        re = RecommendationEngine(conn)
        
        re.log_feedback(request.event_id, request.rec_id, request.accepted, request.outcome)
        
        conn.close()
        return {"status": "feedback_recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback-analytics")
def feedback_analytics():
    """Get feedback analytics."""
    try:
        conn = get_connection()
        analytics = get_feedback_analytics(conn)
        conn.close()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/initialize-data")
def initialize_data(num_events: int = 200):
    """Generate synthetic data for testing."""
    try:
        gen = SyntheticGradeChangeGenerator(num_events=num_events)
        gen.generate_all_events()
        
        # Train models
        from feature_engineering import process_all_events
        process_all_events()
        train_all_models()
        
        return {"status": "data_initialized", "num_events": num_events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    """Get system statistics."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count events by outcome
        cursor.execute("""
            SELECT outcome_label, COUNT(*) as count
            FROM grade_changes
            GROUP BY outcome_label
        """)
        outcomes = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average deviation
        cursor.execute("SELECT AVG(max_deviation_pct) FROM grade_changes")
        avg_deviation = cursor.fetchone()[0] or 0
        
        # Average stabilization time
        cursor.execute("SELECT AVG(time_to_stabilize_sec) FROM grade_changes")
        avg_stab_time = cursor.fetchone()[0] or 0
        
        # Count recommendations
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recs = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "outcomes": outcomes,
            "avg_deviation_pct": float(avg_deviation),
            "avg_stabilization_sec": float(avg_stab_time),
            "total_recommendations": total_recs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
