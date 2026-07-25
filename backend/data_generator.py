"""Synthetic data generator for paper mill grade-change events."""
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import random

from database import init_db, get_connection

np.random.seed(42)
random.seed(42)

# Grade definitions (realistic paper mill grades)
GRADES = {
    "COPY20": {"basis_weight": 80, "filler_pct": 18, "stock_flow_range": (800, 1000), "steam_pressure": 3.5},
    "COPY24": {"basis_weight": 95, "filler_pct": 20, "stock_flow_range": (950, 1150), "steam_pressure": 3.8},
    "NEWSPRINT": {"basis_weight": 52, "filler_pct": 12, "stock_flow_range": (600, 750), "steam_pressure": 3.0},
    "MAGAZINE": {"basis_weight": 120, "filler_pct": 25, "stock_flow_range": (1100, 1300), "steam_pressure": 4.2},
    "BOND": {"basis_weight": 75, "filler_pct": 8, "stock_flow_range": (700, 850), "steam_pressure": 3.2},
}

GRADE_PAIRS = [
    ("COPY20", "COPY24"),
    ("COPY24", "COPY20"),
    ("NEWSPRINT", "COPY24"),
    ("COPY24", "MAGAZINE"),
    ("MAGAZINE", "BOND"),
    ("BOND", "COPY20"),
]

class SyntheticGradeChangeGenerator:
    """Generate realistic synthetic grade-change event data."""
    
    def __init__(self, num_events=200):
        self.num_events = num_events
        self.timestamp_base = datetime(2024, 1, 1).timestamp()
        self.event_id_counter = 1000
        
    def generate_event_id(self):
        self.event_id_counter += 1
        return f"GC_{self.event_id_counter}"
    
    def generate_grade_change_trajectory(self, from_grade, to_grade, duration_sec=600):
        """
        Generate a realistic grade-change trajectory.
        Includes lag effects, overshoots, and stabilization.
        """
        from_spec = GRADES[from_grade]
        to_spec = GRADES[to_grade]
        
        # Timeline: ramp up phase (phase 1), transient (phase 2), stabilization (phase 3)
        phase1_duration = int(duration_sec * 0.3)  # 30% for ramp
        phase2_duration = int(duration_sec * 0.4)  # 40% for transient
        phase3_duration = int(duration_sec * 0.3)  # 30% for stabilization
        
        timestamps = np.arange(0, duration_sec, 5)  # 5-second resolution
        num_points = len(timestamps)
        
        # Initialize arrays
        stock_flow = np.zeros(num_points)
        filler_flow = np.zeros(num_points)
        steam_pressure = np.zeros(num_points)
        machine_speed = np.zeros(num_points)
        basis_weight = np.zeros(num_points)
        moisture = np.zeros(num_points)
        ash = np.zeros(num_points)
        caliper = np.zeros(num_points)
        
        # Starting values
        stock_flow[0] = np.mean(from_spec["stock_flow_range"])
        filler_flow[0] = from_spec["filler_pct"] * stock_flow[0] / 100
        steam_pressure[0] = from_spec["steam_pressure"]
        machine_speed[0] = 1000  # m/min
        basis_weight[0] = from_spec["basis_weight"]
        moisture[0] = 8.0
        ash[0] = from_spec["filler_pct"]
        caliper[0] = basis_weight[0] / 750  # simplified relationship
        
        target_stock_flow = np.mean(to_spec["stock_flow_range"])
        target_filler_flow = to_spec["filler_pct"] * target_stock_flow / 100
        target_steam_pressure = to_spec["steam_pressure"]
        target_basis_weight = to_spec["basis_weight"]
        
        # Generate trajectory
        for i in range(1, num_points):
            t = timestamps[i]
            phase_ratio = t / duration_sec
            
            # Phase 1: Ramp (0-30%)
            if phase_ratio < 0.3:
                ramp_progress = phase_ratio / 0.3
                # PID-like ramp with overshoot
                stock_flow[i] = stock_flow[0] + (target_stock_flow - stock_flow[0]) * ramp_progress
                filler_flow[i] = filler_flow[0] + (target_filler_flow - filler_flow[0]) * ramp_progress
                steam_pressure[i] = steam_pressure[0] + (target_steam_pressure - steam_pressure[0]) * ramp_progress
                machine_speed[i] = machine_speed[0] + (1100 - machine_speed[0]) * ramp_progress * 0.5
                
                # Basis weight lags filler flow by ~60 seconds
                lag_idx = max(0, i - 12)
                basis_weight[i] = basis_weight[0] + (target_basis_weight - basis_weight[0]) * max(0, (t - 60) / (phase1_duration + phase2_duration - 60))
                
            # Phase 2: Transient (30-70%)
            elif phase_ratio < 0.7:
                transient_ratio = (phase_ratio - 0.3) / 0.4
                # Overshoot and oscillation
                overshoot = 1.05 * (1 - np.cos(transient_ratio * np.pi)) / 2
                
                stock_flow[i] = target_stock_flow + (target_stock_flow - stock_flow[0]) * 0.05 * np.sin(transient_ratio * 2 * np.pi)
                filler_flow[i] = target_filler_flow * (1 + 0.08 * np.sin(transient_ratio * 3 * np.pi))
                steam_pressure[i] = target_steam_pressure * (1 + 0.06 * np.sin(transient_ratio * 2.5 * np.pi))
                machine_speed[i] = 1100 + 50 * np.sin(transient_ratio * np.pi)
                
                # Basis weight responds to filler + moisture interaction
                filler_contribution = (filler_flow[i] / target_filler_flow - 1) * 3  # 3 gsm per % filler change
                moisture_contribution = (moisture[i] - 8.0) * 0.5  # 0.5 gsm per % moisture change
                basis_weight[i] = target_basis_weight + filler_contribution + moisture_contribution + \
                                 (target_basis_weight - basis_weight[0]) * 0.1 * np.sin(transient_ratio * np.pi)
                
            # Phase 3: Stabilization (70-100%)
            else:
                stabilization_ratio = (phase_ratio - 0.7) / 0.3
                # Exponential decay to target
                decay = np.exp(-stabilization_ratio * 3)
                
                stock_flow[i] = target_stock_flow + (stock_flow[max(0, i-1)] - target_stock_flow) * decay
                filler_flow[i] = target_filler_flow + (filler_flow[max(0, i-1)] - target_filler_flow) * decay
                steam_pressure[i] = target_steam_pressure + (steam_pressure[max(0, i-1)] - target_steam_pressure) * decay
                machine_speed[i] = 1100 + (machine_speed[max(0, i-1)] - 1100) * decay * 0.5
                
                basis_weight[i] = target_basis_weight + (basis_weight[max(0, i-1)] - target_basis_weight) * decay
            
            # Secondary variables
            moisture[i] = 8.0 - (steam_pressure[i] - 3.0) * 0.5 + np.random.normal(0, 0.1)
            ash[i] = filler_flow[i] / stock_flow[i] * 100 if stock_flow[i] > 0 else 0
            caliper[i] = basis_weight[i] / 750 + np.random.normal(0, 0.002)
            
            # Add realistic noise
            basis_weight[i] += np.random.normal(0, 0.3)
            stock_flow[i] += np.random.normal(0, 5)
            filler_flow[i] += np.random.normal(0, 1)
        
        # Determine outcome
        max_deviation = np.max(np.abs((basis_weight - target_basis_weight) / target_basis_weight * 100))
        success_threshold = 2.5
        
        # Inject failures randomly (30% off-spec rate)
        if random.random() < 0.3:
            # Amplify deviations for failure cases
            basis_weight = basis_weight * (1 + np.random.uniform(0.02, 0.08))
            max_deviation = np.max(np.abs((basis_weight - target_basis_weight) / target_basis_weight * 100))
            outcome = "OFF_SPEC" if max_deviation > success_threshold else "MARGINAL"
        else:
            outcome = "SUCCESS" if max_deviation < success_threshold else "MARGINAL"
        
        # Find time to stabilize (when deviation stays within ±1%)
        stabilized_idx = None
        for idx in range(len(basis_weight) - 20):
            if np.max(np.abs((basis_weight[idx:idx+20] - target_basis_weight) / target_basis_weight * 100)) < 1.0:
                stabilized_idx = idx
                break
        
        time_to_stabilize = timestamps[stabilized_idx] if stabilized_idx else duration_sec
        
        return {
            "timestamps": timestamps,
            "stock_flow": stock_flow,
            "filler_flow": filler_flow,
            "steam_pressure": steam_pressure,
            "machine_speed": machine_speed,
            "basis_weight": basis_weight,
            "moisture": moisture,
            "ash": ash,
            "caliper": caliper,
            "outcome": outcome,
            "max_deviation": max_deviation,
            "time_to_stabilize": int(time_to_stabilize),
            "target_basis_weight": target_basis_weight,
        }
    
    def generate_all_events(self):
        """Generate all synthetic grade-change events."""
        init_db()
        conn = get_connection()
        cursor = conn.cursor()
        
        base_timestamp = self.timestamp_base
        
        for event_num in range(self.num_events):
            event_id = self.generate_event_id()
            from_grade, to_grade = random.choice(GRADE_PAIRS)
            
            # Random duration (480-720 seconds = 8-12 minutes)
            duration = random.randint(480, 720)
            
            timestamp_start = base_timestamp + event_num * 3600  # 1 hour apart
            timestamp_end = timestamp_start + duration
            
            # Generate trajectory
            trajectory = self.generate_grade_change_trajectory(from_grade, to_grade, duration)
            
            # Recipe limits
            recipe_limits = {
                "stock_flow": [600, 1400],
                "filler_flow": [50, 350],
                "steam_pressure": [2.5, 4.5],
                "machine_speed": [800, 1200],
                "basis_weight": [trajectory["target_basis_weight"] * 0.975, trajectory["target_basis_weight"] * 1.025],
            }
            
            # Insert grade change event
            cursor.execute("""
                INSERT INTO grade_changes 
                (event_id, timestamp_start, timestamp_end, from_grade, to_grade, 
                 recipe_target_basis_weight, recipe_limits, outcome_label, 
                 time_to_stabilize_sec, max_deviation_pct, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                timestamp_start,
                timestamp_end,
                from_grade,
                to_grade,
                trajectory["target_basis_weight"],
                json.dumps(recipe_limits),
                trajectory["outcome"],
                trajectory["time_to_stabilize"],
                trajectory["max_deviation"],
                datetime.now().timestamp(),
            ))
            
            # Insert historian data
            for t_idx, ts in enumerate(trajectory["timestamps"]):
                cursor.execute("""
                    INSERT INTO historian 
                    (event_id, timestamp, stock_flow, filler_flow, steam_pressure, 
                     machine_speed, basis_weight, moisture, ash, caliper)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    timestamp_start + ts,
                    trajectory["stock_flow"][t_idx],
                    trajectory["filler_flow"][t_idx],
                    trajectory["steam_pressure"][t_idx],
                    trajectory["machine_speed"][t_idx],
                    trajectory["basis_weight"][t_idx],
                    trajectory["moisture"][t_idx],
                    trajectory["ash"][t_idx],
                    trajectory["caliper"][t_idx],
                ))
            
            # Insert some random operator actions
            if random.random() < 0.3:  # 30% of events have operator interventions
                action_time = timestamp_start + random.randint(int(duration * 0.2), int(duration * 0.6))
                action_var = random.choice(["stock_flow", "steam_pressure", "machine_speed"])
                cursor.execute("""
                    INSERT INTO operator_actions 
                    (event_id, timestamp, variable_changed, old_value, new_value, operator_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    action_time,
                    action_var,
                    np.random.uniform(600, 1200) if action_var == "stock_flow" else np.random.uniform(3.0, 4.5),
                    np.random.uniform(600, 1200) if action_var == "stock_flow" else np.random.uniform(3.0, 4.5),
                    f"OP_{random.randint(1001, 1010)}",
                ))
            
            # Insert alarms for marginal/off-spec events
            if trajectory["outcome"] != "SUCCESS" and random.random() < 0.7:
                alarm_time = timestamp_start + random.randint(int(duration * 0.3), int(duration * 0.8))
                cursor.execute("""
                    INSERT INTO alarms 
                    (event_id, timestamp, alarm_code, severity, variable)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event_id,
                    alarm_time,
                    f"ALM_{random.randint(100, 999)}",
                    "WARNING" if trajectory["outcome"] == "MARGINAL" else "CRITICAL",
                    "BASIS_WEIGHT",
                ))
            
            if (event_num + 1) % 50 == 0:
                print(f"Generated {event_num + 1}/{self.num_events} events")
        
        conn.commit()
        conn.close()
        print(f"\n✅ Generated {self.num_events} grade-change events in database")
        print(f"Database location: backend/data/control_system.db")

if __name__ == "__main__":
    gen = SyntheticGradeChangeGenerator(num_events=200)
    gen.generate_all_events()
