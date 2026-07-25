"""Feature engineering and correlation discovery engine."""
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from scipy.signal import correlate
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
from database import get_connection
from typing import Dict, List, Tuple
import json

KNOWN_CONTROL_LOOPS = {
    ("filler_flow", "ash"): "Direct filler contribution to ash content",
    ("filler_flow", "basis_weight"): "Known MPC loop: filler → basis weight",
    ("stock_flow", "basis_weight"): "Known MPC loop: stock flow → basis weight",
    ("steam_pressure", "moisture"): "Known MPC loop: steam pressure → moisture",
    ("machine_speed", "stock_flow"): "Known MPC loop: machine speed requires stock flow adjustment",
    ("moisture", "basis_weight"): "Measurement drift: moisture sensor affects BW reading",
}

class FeatureEngineer:
    """Extract features from historian time-series data."""
    
    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.scaler = StandardScaler()
    
    def get_event_data(self, event_id: str) -> pd.DataFrame:
        """Fetch historian data for an event."""
        query = """
            SELECT timestamp, stock_flow, filler_flow, steam_pressure, 
                   machine_speed, basis_weight, moisture, ash, caliper
            FROM historian
            WHERE event_id = ?
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, self.conn, params=(event_id,))
        return df
    
    def extract_rolling_features(self, series: np.ndarray, window_sizes=[30, 60, 120]) -> Dict:
        """Extract rolling statistics."""
        features = {}
        for window in window_sizes:
            if len(series) < window:
                continue
            series_df = pd.Series(series)
            features[f"rolling_mean_{window}s"] = series_df.rolling(window).mean().values[-1]
            features[f"rolling_std_{window}s"] = series_df.rolling(window).std().values[-1]
            features[f"rolling_min_{window}s"] = series_df.rolling(window).min().values[-1]
            features[f"rolling_max_{window}s"] = series_df.rolling(window).max().values[-1]
        return features
    
    def extract_rate_of_change(self, series: np.ndarray, dt: float = 5.0) -> Dict:
        """Extract rate-of-change features."""
        diffs = np.diff(series)
        return {
            "roc_mean": np.mean(diffs),
            "roc_std": np.std(diffs),
            "roc_max": np.max(np.abs(diffs)),
            "roc_skew": np.mean(diffs ** 3) / (np.std(diffs) ** 3 + 1e-6),
        }
    
    def extract_lag_features(self, series1: np.ndarray, series2: np.ndarray, max_lag: int = 30) -> Dict:
        """Detect lag between two signals using cross-correlation."""
        # Normalize signals
        s1 = (series1 - np.mean(series1)) / (np.std(series1) + 1e-6)
        s2 = (series2 - np.mean(series2)) / (np.std(series2) + 1e-6)
        
        # Cross-correlation
        xcorr = correlate(s1, s2, mode='same')
        lag = np.argmax(np.abs(xcorr)) - len(xcorr) // 2
        correlation_strength = np.max(np.abs(xcorr)) / len(xcorr)
        
        return {
            "lag_samples": lag,
            "lag_seconds": lag * 5,  # 5s resolution
            "xcorr_strength": correlation_strength,
        }
    
    def extract_all_features(self, event_id: str) -> Dict:
        """Extract comprehensive feature set for an event."""
        df = self.get_event_data(event_id)
        
        if df.empty:
            return {}
        
        features = {"event_id": event_id}
        
        variables = ["stock_flow", "filler_flow", "steam_pressure", 
                    "machine_speed", "basis_weight", "moisture", "ash", "caliper"]
        
        # Extract rolling and rate-of-change features for each variable
        for var in variables:
            if var in df.columns:
                series = df[var].values
                features.update(self.extract_rolling_features(series))
                features.update({f"{var}_" + k: v for k, v in self.extract_rate_of_change(series).items()})
                features[f"{var}_initial"] = series[0]
                features[f"{var}_final"] = series[-1]
                features[f"{var}_change"] = series[-1] - series[0]
                features[f"{var}_volatility"] = np.std(series)
        
        # Extract lag features between key variable pairs
        for var1, var2 in [("filler_flow", "basis_weight"), 
                          ("steam_pressure", "moisture"),
                          ("stock_flow", "basis_weight")]:
            if var1 in df.columns and var2 in df.columns:
                lag_feats = self.extract_lag_features(df[var1].values, df[var2].values)
                features.update({f"lag_{var1}_to_{var2}_" + k: v for k, v in lag_feats.items()})
        
        return features


class CorrelationEngine:
    """Discover correlations between variables, both known and novel."""
    
    def __init__(self, conn=None):
        self.conn = conn or get_connection()
        self.fe = FeatureEngineer(conn)
        self.correlation_cache = {}
    
    def compute_correlation(self, series1: np.ndarray, series2: np.ndarray, method: str = "pearson") -> float:
        """Compute correlation between two series."""
        if len(series1) < 3 or len(series2) < 3:
            return 0.0
        
        try:
            if method == "pearson":
                corr, _ = pearsonr(series1, series2)
            elif method == "spearman":
                corr, _ = spearmanr(series1, series2)
            else:
                corr = 0.0
            return abs(corr)  # Use absolute value
        except:
            return 0.0
    
    def compute_mutual_information(self, series1: np.ndarray, series2: np.ndarray, bins: int = 10) -> float:
        """Compute mutual information between two continuous series."""
        # Discretize series into bins
        hist_2d, _, _ = np.histogram2d(series1, series2, bins=bins)
        pxy = hist_2d / np.sum(hist_2d)
        px = np.sum(pxy, axis=1)
        py = np.sum(pxy, axis=0)
        
        px_py = px[:, None] * py[None, :]
        
        # Avoid log(0)
        nzs = pxy > 0
        mi = np.sum(pxy[nzs] * np.log(pxy[nzs] / px_py[nzs]))
        return abs(mi)
    
    def discover_correlations_for_event(self, event_id: str, min_threshold: float = 0.3) -> List[Dict]:
        """Discover all significant correlations in an event's data."""
        df = self.fe.get_event_data(event_id)
        
        if df.empty:
            return []
        
        variables = ["stock_flow", "filler_flow", "steam_pressure", 
                    "machine_speed", "basis_weight", "moisture", "ash", "caliper"]
        available_vars = [v for v in variables if v in df.columns]
        
        correlations = []
        
        # Compute pairwise correlations
        for i, var1 in enumerate(available_vars):
            for var2 in available_vars[i+1:]:
                series1 = df[var1].values
                series2 = df[var2].values
                
                # Pearson correlation
                pearson_corr = self.compute_correlation(series1, series2, method="pearson")
                
                # Mutual information
                mi = self.compute_mutual_information(series1, series2)
                
                # Combined score
                combined_score = (pearson_corr + mi / np.log(2)) / 2  # Normalize MI
                
                if combined_score >= min_threshold:
                    is_known = (var1, var2) in KNOWN_CONTROL_LOOPS or (var2, var1) in KNOWN_CONTROL_LOOPS
                    
                    correlation_record = {
                        "var1": var1,
                        "var2": var2,
                        "correlation_strength": float(pearson_corr),
                        "mutual_information": float(mi),
                        "combined_score": float(combined_score),
                        "is_known_loop": 1 if is_known else 0,
                        "known_loop_description": KNOWN_CONTROL_LOOPS.get((var1, var2), KNOWN_CONTROL_LOOPS.get((var2, var1), "")),
                    }
                    correlations.append(correlation_record)
        
        return sorted(correlations, key=lambda x: x["combined_score"], reverse=True)
    
    def compute_impact_on_basis_weight(self, event_id: str, variable: str) -> str:
        """Compute estimated impact of a variable on basis weight."""
        df = self.fe.get_event_data(event_id)
        
        if df.empty or variable not in df.columns:
            return "Unknown"
        
        # Normalize variables
        var_data = (df[variable].values - np.mean(df[variable])) / (np.std(df[variable]) + 1e-6)
        bw_data = (df["basis_weight"].values - np.mean(df["basis_weight"])) / (np.std(df["basis_weight"]) + 1e-6)
        
        # Compute cross-correlation at different lags
        xcorr = correlate(var_data, bw_data, mode='same')
        max_xcorr = np.max(np.abs(xcorr))
        
        # Estimate impact magnitude
        if max_xcorr > 0.7:
            impact = "STRONG"
        elif max_xcorr > 0.4:
            impact = "MODERATE"
        elif max_xcorr > 0.2:
            impact = "WEAK"
        else:
            impact = "NEGLIGIBLE"
        
        # Estimate direction
        lag = np.argmax(np.abs(xcorr)) - len(xcorr) // 2
        direction = "POSITIVE" if xcorr[np.argmax(np.abs(xcorr))] > 0 else "NEGATIVE"
        
        return f"{impact} {direction} impact (lag: {lag*5}s)"
    
    def store_correlations(self, event_id: str):
        """Discover and store correlations for an event."""
        correlations = self.discover_correlations_for_event(event_id)
        
        cursor = self.conn.cursor()
        
        for corr in correlations:
            cursor.execute("""
                INSERT INTO correlations 
                (var1, var2, correlation_strength, is_known_loop, impact_on_basis_weight, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                corr["var1"],
                corr["var2"],
                corr["correlation_strength"],
                corr["is_known_loop"],
                self.compute_impact_on_basis_weight(event_id, corr["var1"]),
                __import__("time").time(),
            ))
        
        self.conn.commit()
    
    def get_new_correlations(self, min_threshold: float = 0.4) -> List[Dict]:
        """Get all newly discovered (not known) correlations from database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT var1, var2, correlation_strength, impact_on_basis_weight
            FROM correlations
            WHERE is_known_loop = 0 AND correlation_strength > ?
            ORDER BY correlation_strength DESC
        """, (min_threshold,))
        
        rows = cursor.fetchall()
        return [{
            "var1": row[0],
            "var2": row[1],
            "strength": row[2],
            "impact": row[3],
        } for row in rows]


def process_all_events():
    """Process all events to extract features and discover correlations."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all event IDs
    cursor.execute("SELECT event_id FROM grade_changes ORDER BY timestamp_start DESC")
    events = cursor.fetchall()
    
    ce = CorrelationEngine(conn)
    
    print(f"Processing {len(events)} events for feature extraction and correlation discovery...")
    
    for idx, (event_id,) in enumerate(events):
        try:
            ce.store_correlations(event_id)
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(events)} events")
        except Exception as e:
            print(f"  Error processing {event_id}: {e}")
    
    print(f"\n✅ Feature extraction complete")
    
    # Display sample new correlations
    new_corrs = ce.get_new_correlations()
    if new_corrs:
        print(f"\n🔍 Sample newly discovered correlations:")
        for corr in new_corrs[:5]:
            print(f"  {corr['var1']} ↔ {corr['var2']}: strength={corr['strength']:.3f}, impact={corr['impact']}")
    
    conn.close()

if __name__ == "__main__":
    process_all_events()
