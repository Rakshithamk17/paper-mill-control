"""Integration tests for paper mill control system."""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / ".." / "backend"))

from database import init_db, get_connection
from data_generator import SyntheticGradeChangeGenerator
from feature_engineering import FeatureEngineer, CorrelationEngine
from models import DeviationRiskModel, StabilizationTimeModel
from recommender import RecommendationEngine

class TestDataGeneration:
    def test_synthetic_data_generation(self):
        """Test that synthetic data is generated correctly."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=10)
        gen.generate_all_events()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM grade_changes")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count >= 10, "Synthetic data not generated"

class TestFeatureEngineering:
    def test_feature_extraction(self):
        """Test that features are extracted correctly."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=5)
        gen.generate_all_events()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM grade_changes LIMIT 1")
        event_id = cursor.fetchone()[0]
        
        fe = FeatureEngineer(conn)
        features = fe.extract_all_features(event_id)
        
        conn.close()
        
        assert features is not None, "Features not extracted"
        assert len(features) > 0, "No features extracted"
        assert "event_id" in features, "Event ID not in features"

class TestCorrelationDiscovery:
    def test_correlation_discovery(self):
        """Test that correlations are discovered."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=5)
        gen.generate_all_events()
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM grade_changes LIMIT 1")
        event_id = cursor.fetchone()[0]
        
        ce = CorrelationEngine(conn)
        correlations = ce.discover_correlations_for_event(event_id)
        
        conn.close()
        
        assert isinstance(correlations, list), "Correlations not returned as list"
        # May be empty if no correlations found, which is OK

class TestModelTraining:
    def test_deviation_risk_model_training(self):
        """Test that deviation risk model trains."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=50)
        gen.generate_all_events()
        
        drm = DeviationRiskModel()
        success = drm.train()
        
        assert success, "Model training failed"
        assert drm.is_trained, "Model not marked as trained"
        assert drm.model is not None, "Model not created"
    
    def test_stabilization_time_model_training(self):
        """Test that stabilization time model trains."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=50)
        gen.generate_all_events()
        
        stm = StabilizationTimeModel()
        success = stm.train()
        
        assert success, "Model training failed"
        assert stm.is_trained, "Model not marked as trained"
        assert stm.model is not None, "Model not created"

class TestRecommendationEngine:
    def test_recommendation_generation(self):
        """Test that recommendations are generated."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=50)
        gen.generate_all_events()
        
        # Train models first
        drm = DeviationRiskModel()
        drm.train()
        
        stm = StabilizationTimeModel()
        stm.train()
        
        # Generate recommendations
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM grade_changes LIMIT 1")
        event_id = cursor.fetchone()[0]
        
        re = RecommendationEngine(conn)
        recommendations = re.generate_recommendations(event_id)
        
        conn.close()
        
        assert isinstance(recommendations, list), "Recommendations not a list"
        # Recommendations may be empty for low-risk events

class TestConstraintChecking:
    def test_recommendation_constraints(self):
        """Test that recommendations respect constraints."""
        init_db()
        gen = SyntheticGradeChangeGenerator(num_events=50)
        gen.generate_all_events()
        
        # Train models
        drm = DeviationRiskModel()
        drm.train()
        stm = StabilizationTimeModel()
        stm.train()
        
        # Check recommendations
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM grade_changes LIMIT 1")
        event_id = cursor.fetchone()[0]
        
        re = RecommendationEngine(conn)
        recipe_limits = re.get_recipe_limits(event_id)
        recommendations = re.generate_recommendations(event_id)
        
        for rec in recommendations:
            var = rec["variable"]
            recommended_val = rec["recommended_value"]
            
            if var in recipe_limits:
                min_val, max_val = recipe_limits[var]
                assert min_val <= recommended_val <= max_val, f"Recommendation violates constraints for {var}"
        
        conn.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
