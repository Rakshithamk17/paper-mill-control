"""SQLite database setup for paper mill control system."""
import sqlite3
from pathlib import Path
import json

DB_PATH = Path("backend/data/control_system.db")

def init_db():
    """Initialize database schema."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Grade change events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grade_changes (
            event_id TEXT PRIMARY KEY,
            timestamp_start REAL,
            timestamp_end REAL,
            from_grade TEXT,
            to_grade TEXT,
            recipe_target_basis_weight REAL,
            recipe_limits TEXT,
            outcome_label TEXT,
            time_to_stabilize_sec INTEGER,
            max_deviation_pct REAL,
            created_at REAL
        )
    """)
    
    # Time-series historian (1-5s resolution)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historian (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            timestamp REAL,
            stock_flow REAL,
            filler_flow REAL,
            steam_pressure REAL,
            machine_speed REAL,
            basis_weight REAL,
            moisture REAL,
            ash REAL,
            caliper REAL,
            FOREIGN KEY (event_id) REFERENCES grade_changes(event_id)
        )
    """)
    
    # Operator action log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operator_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            timestamp REAL,
            variable_changed TEXT,
            old_value REAL,
            new_value REAL,
            operator_id TEXT,
            FOREIGN KEY (event_id) REFERENCES grade_changes(event_id)
        )
    """)
    
    # Alarm/scanner diagnostics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            timestamp REAL,
            alarm_code TEXT,
            severity TEXT,
            variable TEXT,
            FOREIGN KEY (event_id) REFERENCES grade_changes(event_id)
        )
    """)
    
    # Recommendations and feedback
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            timestamp REAL,
            variable TEXT,
            recommended_value REAL,
            expected_effect TEXT,
            source_tag TEXT,
            rationale TEXT,
            accepted INTEGER,
            operator_id TEXT,
            outcome TEXT,
            FOREIGN KEY (event_id) REFERENCES grade_changes(event_id)
        )
    """)
    
    # Correlations discovered
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            var1 TEXT,
            var2 TEXT,
            correlation_strength REAL,
            is_known_loop INTEGER,
            impact_on_basis_weight TEXT,
            discovered_at REAL
        )
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
