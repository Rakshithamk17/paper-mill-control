"""Prediction models for basis weight deviation risk and stabilization time."""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path
import json
from database import get_connection
from feature_engineering import FeatureEngineer

MODEL_DIR = Path("backend/models")
MODEL_DIR.mkdir(exist_ok=True)

class DeviationRiskModel:
    """Predicts probability and time-to-breach of Basis Weight ±2.5% band."""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
    
    def prepare_training_data(self, conn=None):
        """Prepare training data from historical events."""
        conn = conn or get_connection()
        fe = FeatureEngineer(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT event_id, max_deviation_pct, outcome_label FROM grade_changes ORDER BY timestamp_start DESC")
        events = cursor.fetchall()
        
        X, y = [], []
        
        print(f"Preparing training data from {len(events)} events...")
        
        for event_id, max_deviation, outcome in events:
            try:
                features = fe.extract_all_features(event_id)
                if not features:
                    continue
                
                self.feature_names = list(features.keys())
                X.append([features.get(k, 0) for k in self.feature_names])
                
                # Binary classification: will breach ±2.5% or not
                y.append(1 if max_deviation > 2.5 else 0)
            except:
                continue
        
        return np.array(X), np.array(y)
    
    def train(self, conn=None):
        """Train the deviation risk classifier."""
        X, y = self.prepare_training_data(conn)
        
        if len(X) < 10:
            print("❌ Insufficient data for training")
            return False
        
        # Remove features with all zeros
        mask = np.std(X, axis=0) > 1e-6
        X = X[:, mask]
        self.feature_names = [f for i, f in enumerate(self.feature_names) if mask[i]]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        # Train model
        self.model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n✅ Deviation Risk Model trained")
        print(f"   Train Accuracy: {train_score:.3f}")
        print(f"   Test Accuracy: {test_score:.3f}")
        
        self.is_trained = True
        self.save()
        return True
    
    def predict_risk(self, features_dict: dict) -> dict:
        """Predict risk for a set of features."""
        if not self.is_trained:
            return {"error": "Model not trained"}
        
        try:
            X = np.array([[features_dict.get(f, 0) for f in self.feature_names]])
            X = self.scaler.transform(X)
            
            risk_prob = self.model.predict_proba(X)[0, 1]  # Probability of breach
            feature_importance = self._get_feature_importance()
            
            return {
                "risk_probability": float(risk_prob),
                "will_breach": risk_prob > 0.5,
                "top_risk_drivers": feature_importance[:5],
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_feature_importance(self) -> list:
        """Get top feature importances."""
        if self.model is None:
            return []
        
        importances = self.model.feature_importances_
        top_idx = np.argsort(importances)[::-1][:5]
        
        return [{
            "feature": self.feature_names[i],
            "importance": float(importances[i])
        } for i in top_idx]
    
    def save(self):
        joblib.dump(self.model, MODEL_DIR / "deviation_risk_model.pkl")
        joblib.dump(self.scaler, MODEL_DIR / "deviation_risk_scaler.pkl")
        with open(MODEL_DIR / "deviation_risk_features.json", "w") as f:
            json.dump(self.feature_names, f)
    
    def load(self):
        if (MODEL_DIR / "deviation_risk_model.pkl").exists():
            self.model = joblib.load(MODEL_DIR / "deviation_risk_model.pkl")
            self.scaler = joblib.load(MODEL_DIR / "deviation_risk_scaler.pkl")
            with open(MODEL_DIR / "deviation_risk_features.json") as f:
                self.feature_names = json.load(f)
            self.is_trained = True


class StabilizationTimeModel:
    """Predicts time-to-stabilize and ranks variables by settling impact."""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
    
    def prepare_training_data(self, conn=None):
        """Prepare training data from historical events."""
        conn = conn or get_connection()
        fe = FeatureEngineer(conn)
        
        cursor = conn.cursor()
        cursor.execute("SELECT event_id, time_to_stabilize_sec FROM grade_changes ORDER BY timestamp_start DESC")
        events = cursor.fetchall()
        
        X, y = [], []
        
        print(f"Preparing stabilization training data from {len(events)} events...")
        
        for event_id, time_to_stabilize in events:
            try:
                features = fe.extract_all_features(event_id)
                if not features:
                    continue
                
                self.feature_names = list(features.keys())
                X.append([features.get(k, 0) for k in self.feature_names])
                y.append(time_to_stabilize)
            except:
                continue
        
        return np.array(X), np.array(y)
    
    def train(self, conn=None):
        """Train the stabilization time regressor."""
        X, y = self.prepare_training_data(conn)
        
        if len(X) < 10:
            print("❌ Insufficient data for stabilization model training")
            return False
        
        # Remove features with all zeros
        mask = np.std(X, axis=0) > 1e-6
        X = X[:, mask]
        self.feature_names = [f for i, f in enumerate(self.feature_names) if mask[i]]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n✅ Stabilization Time Model trained")
        print(f"   Train R²: {train_score:.3f}")
        print(f"   Test R²: {test_score:.3f}")
        
        self.is_trained = True
        self.save()
        return True
    
    def predict_stabilization_time(self, features_dict: dict) -> dict:
        """Predict time-to-stabilize and get key drivers."""
        if not self.is_trained:
            return {"error": "Model not trained"}
        
        try:
            X = np.array([[features_dict.get(f, 0) for f in self.feature_names]])
            X = self.scaler.transform(X)
            
            predicted_time = self.model.predict(X)[0]
            drivers = self._get_feature_importance()
            
            return {
                "predicted_stabilization_sec": max(0, float(predicted_time)),
                "stabilization_drivers": drivers[:5],
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_feature_importance(self) -> list:
        """Get top feature importances (stabilization drivers)."""
        if self.model is None:
            return []
        
        importances = self.model.feature_importances_
        top_idx = np.argsort(importances)[::-1][:5]
        
        return [{
            "variable": self.feature_names[i],
            "impact_on_settling": float(importances[i])
        } for i in top_idx]
    
    def save(self):
        joblib.dump(self.model, MODEL_DIR / "stabilization_time_model.pkl")
        joblib.dump(self.scaler, MODEL_DIR / "stabilization_time_scaler.pkl")
        with open(MODEL_DIR / "stabilization_time_features.json", "w") as f:
            json.dump(self.feature_names, f)
    
    def load(self):
        if (MODEL_DIR / "stabilization_time_model.pkl").exists():
            self.model = joblib.load(MODEL_DIR / "stabilization_time_model.pkl")
            self.scaler = joblib.load(MODEL_DIR / "stabilization_time_scaler.pkl")
            with open(MODEL_DIR / "stabilization_time_features.json") as f:
                self.feature_names = json.load(f)
            self.is_trained = True


def train_all_models():
    """Train all prediction models."""
    conn = get_connection()
    
    print("=" * 60)
    print("TRAINING PREDICTION MODELS")
    print("=" * 60)
    
    drm = DeviationRiskModel()
    drm.train(conn)
    
    stm = StabilizationTimeModel()
    stm.train(conn)
    
    conn.close()
    print("\n✅ All models trained and saved")

if __name__ == "__main__":
    train_all_models()
