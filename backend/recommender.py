"""Recommendation engine with constraint checking and source tagging."""
import numpy as np
import json
from database import get_connection
from feature_engineering import FeatureEngineer, CorrelationEngine
from models import DeviationRiskModel, StabilizationTimeModel
from typing import Dict, List, Optional
from datetime import datetime

class RecommendationEngine:
    """Generate setpoint recommendations with explainability and constraint checking."""
    
    SOURCE_TAGS = {
        "historical_data": "Based on similar historical transitions",
        "recipe_constraint": "Within recipe limits",
        "correlation_model": "Derived from discovered correlations",
        "operator_pattern": "Learned from operator interventions",
        "stabilization_driver": "Addresses slow settling drivers",
        "risk_mitigation": "Mitigates predicted breach risk",
    }
    
    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.fe = FeatureEngineer(conn)
        self.ce = CorrelationEngine(conn)
        self.drm = DeviationRiskModel()
        self.stm = StabilizationTimeModel()
        self.drm.load()
        self.stm.load()
    
    def get_recipe_limits(self, event_id: str) -> Dict:
        """Fetch recipe limits for an event."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT recipe_limits FROM grade_changes WHERE event_id = ?",
            (event_id,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}
    
    def get_current_state(self, event_id: str) -> Dict:
        """Get current process state (most recent measurement)."""
        df = self.fe.get_event_data(event_id)
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        return {
            "stock_flow": latest["stock_flow"],
            "filler_flow": latest["filler_flow"],
            "steam_pressure": latest["steam_pressure"],
            "machine_speed": latest["machine_speed"],
            "basis_weight": latest["basis_weight"],
            "moisture": latest["moisture"],
            "ash": latest["ash"],
            "caliper": latest["caliper"],
        }
    
    def get_grade_targets(self, event_id: str) -> Dict:
        """Get target setpoints for the grade change."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT recipe_target_basis_weight, to_grade FROM grade_changes WHERE event_id = ?",
            (event_id,)
        )
        row = cursor.fetchone()
        if row:
            target_bw, to_grade = row
            # Map grade to typical setpoints (simplified)
            grade_map = {
                "COPY20": {"stock_flow": 900, "steam_pressure": 3.5, "machine_speed": 1000},
                "COPY24": {"stock_flow": 1050, "steam_pressure": 3.8, "machine_speed": 1000},
                "NEWSPRINT": {"stock_flow": 675, "steam_pressure": 3.0, "machine_speed": 1000},
                "MAGAZINE": {"stock_flow": 1200, "steam_pressure": 4.2, "machine_speed": 1000},
                "BOND": {"stock_flow": 775, "steam_pressure": 3.2, "machine_speed": 1000},
            }
            return {"basis_weight": target_bw, **grade_map.get(to_grade, {})}
        return {}
    
    def check_constraint(self, variable: str, value: float, recipe_limits: Dict) -> bool:
        """Check if a value satisfies recipe constraints."""
        if variable not in recipe_limits:
            return True
        
        min_val, max_val = recipe_limits[variable]
        return min_val <= value <= max_val
    
    def constrain_value(self, variable: str, value: float, recipe_limits: Dict) -> float:
        """Constrain a value to recipe limits."""
        if variable not in recipe_limits:
            return value
        
        min_val, max_val = recipe_limits[variable]
        return max(min_val, min(value, max_val))
    
    def recommend_for_risk_mitigation(self, event_id: str, current_state: Dict, recipe_limits: Dict) -> List[Dict]:
        """Generate recommendations to mitigate breach risk."""
        recommendations = []
        features = self.fe.extract_all_features(event_id)
        
        if not features:
            return recommendations
        
        # Get risk prediction
        risk_result = self.drm.predict_risk(features)
        if "error" in risk_result or risk_result["risk_probability"] <= 0.5:
            return recommendations
        
        # If high risk, recommend adjustments to top risk drivers
        for driver in risk_result.get("top_risk_drivers", [])[:2]:
            feature_name = driver["feature"]
            
            # Extract variable name (e.g., "filler_flow_roc_mean" -> "filler_flow")
            var_name = feature_name.split("_")[0]
            
            if var_name not in current_state:
                continue
            
            current_val = current_state[var_name]
            
            # Conservative adjustment: reduce aggressiveness
            if "roc" in feature_name:  # Rate-of-change feature
                # Recommend slower ramp
                recommended = current_val * 0.95 if current_val > 0 else current_val
            else:
                # Recommend moving toward target more gradually
                target = self.get_grade_targets(event_id).get(var_name, current_val)
                recommended = current_val + (target - current_val) * 0.3  # Conservative 30%
            
            recommended = self.constrain_value(var_name, recommended, recipe_limits)
            
            if recommended != current_val:
                recommendations.append({
                    "variable": var_name,
                    "current_value": float(current_val),
                    "recommended_value": float(recommended),
                    "expected_effect": f"Reduce {var_name} aggressiveness to lower breach risk",
                    "source_tag": "risk_mitigation",
                    "rationale": f"Risk prediction shows {var_name} is a key driver. Slower ramp reduces transient overshoot.",
                    "confidence": float(risk_result["risk_probability"]),
                })
        
        return recommendations
    
    def recommend_for_stabilization(self, event_id: str, current_state: Dict, recipe_limits: Dict) -> List[Dict]:
        """Generate recommendations to reduce settling time."""
        recommendations = []
        features = self.fe.extract_all_features(event_id)
        
        if not features:
            return recommendations
        
        # Get stabilization prediction
        stab_result = self.stm.predict_stabilization_time(features)
        if "error" in stab_result:
            return recommendations
        
        predicted_time = stab_result.get("predicted_stabilization_sec", 0)
        
        # If predicted stabilization is slow (> 400 sec), recommend adjustments
        if predicted_time > 400:
            for driver in stab_result.get("stabilization_drivers", [])[:2]:
                var_name = driver["variable"]
                
                if var_name not in current_state:
                    continue
                
                current_val = current_state[var_name]
                target = self.get_grade_targets(event_id).get(var_name, current_val)
                
                # Recommend moving more aggressively toward target
                recommended = current_val + (target - current_val) * 0.7  # More aggressive 70%
                recommended = self.constrain_value(var_name, recommended, recipe_limits)
                
                if abs(recommended - current_val) > 1:  # Minimum change threshold
                    recommendations.append({
                        "variable": var_name,
                        "current_value": float(current_val),
                        "recommended_value": float(recommended),
                        "expected_effect": f"Speed up {var_name} ramp to reduce settling time by ~{int(predicted_time * 0.15)}s",
                        "source_tag": "stabilization_driver",
                        "rationale": f"Analysis shows {var_name} is a key driver of slow settling. Faster ramp accelerates stabilization.",
                        "confidence": float(predicted_time / 600),  # Normalize to 0-1
                    })
        
        return recommendations
    
    def recommend_from_correlations(self, event_id: str, current_state: Dict, recipe_limits: Dict) -> List[Dict]:
        """Generate recommendations based on discovered correlations."""
        recommendations = []
        
        # Get newly discovered correlations
        df = self.fe.get_event_data(event_id)
        if df.empty:
            return recommendations
        
        correlations = self.ce.discover_correlations_for_event(event_id, min_threshold=0.5)
        
        # Focus on correlations involving basis_weight
        bw_correlations = [c for c in correlations if "basis_weight" in [c["var1"], c["var2"]]
                          and c["is_known_loop"] == 0]  # Only novel ones
        
        for corr in bw_correlations[:2]:
            other_var = corr["var1"] if corr["var2"] == "basis_weight" else corr["var2"]
            
            if other_var not in current_state:
                continue
            
            current_val = current_state[other_var]
            target = self.get_grade_targets(event_id).get(other_var, current_val)
            
            # Recommendation: fine-tune correlated variable
            recommended = current_val + (target - current_val) * 0.5
            recommended = self.constrain_value(other_var, recommended, recipe_limits)
            
            if abs(recommended - current_val) > 0.5:
                recommendations.append({
                    "variable": other_var,
                    "current_value": float(current_val),
                    "recommended_value": float(recommended),
                    "expected_effect": f"Fine-tune {other_var} based on discovered correlation with basis_weight",
                    "source_tag": "correlation_model",
                    "rationale": f"Novel correlation detected: {other_var} ↔ basis_weight (strength: {corr['correlation_strength']:.2f}). Adjustment helps stabilize BW.",
                    "confidence": float(corr["correlation_strength"]),
                })
        
        return recommendations
    
    def generate_recommendations(self, event_id: str) -> List[Dict]:
        """Generate all recommendations for an event."""
        current_state = self.get_current_state(event_id)
        recipe_limits = self.get_recipe_limits(event_id)
        
        if not current_state or not recipe_limits:
            return []
        
        all_recommendations = []
        
        # Risk mitigation
        all_recommendations.extend(self.recommend_for_risk_mitigation(event_id, current_state, recipe_limits))
        
        # Stabilization
        all_recommendations.extend(self.recommend_for_stabilization(event_id, current_state, recipe_limits))
        
        # Correlations
        all_recommendations.extend(self.recommend_from_correlations(event_id, current_state, recipe_limits))
        
        # Remove duplicates (same variable recommended multiple times)
        seen_vars = set()
        unique_recs = []
        for rec in all_recommendations:
            if rec["variable"] not in seen_vars:
                unique_recs.append(rec)
                seen_vars.add(rec["variable"])
        
        return sorted(unique_recs, key=lambda x: x["confidence"], reverse=True)
    
    def log_feedback(self, event_id: str, rec_id: int, accepted: bool, outcome: Optional[str] = None):
        """Log operator feedback on a recommendation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recommendations
            SET accepted = ?, outcome = ?
            WHERE id = ?
        """, (1 if accepted else 0, outcome, rec_id))
        self.conn.commit()

def get_feedback_analytics(conn=None) -> Dict:
    """Compute feedback analytics from logged operator decisions."""
    conn = conn or get_connection()
    cursor = conn.cursor()
    
    # Get all recommendations with feedback
    cursor.execute("""
        SELECT accepted, COUNT(*) as count
        FROM recommendations
        WHERE accepted IS NOT NULL
        GROUP BY accepted
    """)
    
    results = cursor.fetchall()
    total = sum(r[1] for r in results)
    accepted_count = next((r[1] for r in results if r[0] == 1), 0)
    
    acceptance_rate = accepted_count / total if total > 0 else 0
    
    return {
        "total_recommendations": total,
        "accepted": accepted_count,
        "rejected": total - accepted_count,
        "acceptance_rate": float(acceptance_rate),
    }

if __name__ == "__main__":
    import sys
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_id FROM grade_changes LIMIT 1")
    event = cursor.fetchone()
    
    if event:
        event_id = event[0]
        re = RecommendationEngine(conn)
        
        print(f"\nGenerating recommendations for event {event_id}...")
        recommendations = re.generate_recommendations(event_id)
        
        if recommendations:
            print(f"\n✅ Generated {len(recommendations)} recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n  {i}. {rec['variable'].upper()}")
                print(f"     Current: {rec['current_value']:.2f} → Recommended: {rec['recommended_value']:.2f}")
                print(f"     Effect: {rec['expected_effect']}")
                print(f"     Source: {rec['source_tag']}")
                print(f"     Rationale: {rec['rationale']}")
                print(f"     Confidence: {rec['confidence']:.2%}")
        else:
            print("\nNo recommendations generated.")
    
    conn.close()
