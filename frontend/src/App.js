import React, { useState, useEffect } from 'react';
import './App.css';
import api from './api';
import LiveTrajectory from './components/LiveTrajectory';
import RiskPanel from './components/RiskPanel';
import CorrelationDiscovery from './components/CorrelationDiscovery';
import FutureStateProjection from './components/FutureStateProjection';
import StabilizationDrivers from './components/StabilizationDrivers';
import RecommendationFeed from './components/RecommendationFeed';
import FeedbackAnalytics from './components/FeedbackAnalytics';

function App() {
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const response = await api.get('/events?limit=20');
      setEvents(response.data.events);
      if (response.data.events.length > 0) {
        setSelectedEvent(response.data.events[0].event_id);
      }
    } catch (error) {
      console.error('Error fetching events:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>📊 Paper Mill Intelligent Process Control</h1>
          <p className="subtitle">Real-time Grade Change Risk Prediction & Recommendation Engine</p>
        </div>
      </header>

      <div className="app-container">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <h3>Recent Grade Changes</h3>
            <div className="event-list">
              {events.map((event) => (
                <div
                  key={event.event_id}
                  className={`event-item ${selectedEvent === event.event_id ? 'active' : ''}`}
                  onClick={() => setSelectedEvent(event.event_id)}
                >
                  <div className="event-header">
                    <span className="event-id">{event.event_id}</span>
                    <span className={`outcome-badge outcome-${event.outcome.toLowerCase()}`}>
                      {event.outcome}
                    </span>
                  </div>
                  <div className="event-details">
                    <p>{event.from_grade} → {event.to_grade}</p>
                    <p>Deviation: {event.max_deviation_pct.toFixed(2)}%</p>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn-secondary" onClick={fetchEvents} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          {selectedEvent ? (
            <>
              <div className="tabs">
                <button
                  className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
                  onClick={() => setActiveTab('overview')}
                >
                  Overview
                </button>
                <button
                  className={`tab-button ${activeTab === 'analysis' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analysis')}
                >
                  Analysis
                </button>
                <button
                  className={`tab-button ${activeTab === 'recommendations' ? 'active' : ''}`}
                  onClick={() => setActiveTab('recommendations')}
                >
                  Recommendations
                </button>
                <button
                  className={`tab-button ${activeTab === 'analytics' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analytics')}
                >
                  Analytics
                </button>
              </div>

              {/* Overview Tab */}
              {activeTab === 'overview' && (
                <div className="tab-content">
                  <div className="grid grid-2">
                    <LiveTrajectory eventId={selectedEvent} />
                    <RiskPanel eventId={selectedEvent} />
                  </div>
                </div>
              )}

              {/* Analysis Tab */}
              {activeTab === 'analysis' && (
                <div className="tab-content">
                  <div className="grid grid-2">
                    <CorrelationDiscovery eventId={selectedEvent} />
                    <FutureStateProjection eventId={selectedEvent} />
                  </div>
                </div>
              )}

              {/* Recommendations Tab */}
              {activeTab === 'recommendations' && (
                <div className="tab-content">
                  <div className="grid grid-2">
                    <StabilizationDrivers eventId={selectedEvent} />
                    <RecommendationFeed eventId={selectedEvent} />
                  </div>
                </div>
              )}

              {/* Analytics Tab */}
              {activeTab === 'analytics' && (
                <div className="tab-content">
                  <FeedbackAnalytics />
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p>No events available. Generate synthetic data to start.</p>
              <button className="btn-primary">Initialize Data</button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
