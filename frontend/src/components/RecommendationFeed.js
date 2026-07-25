import React, { useState, useEffect } from 'react';
import api from '../api';

function RecommendationFeed({ eventId }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState({});

  useEffect(() => {
    if (!eventId) return;

    const fetchRecommendations = async () => {
      try {
        setLoading(true);
        const response = await api.post('/recommend-setpoints', { event_id: eventId });
        setRecommendations(response.data.recommendations);
        setError(null);
      } catch (err) {
        setError('Failed to fetch recommendations');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [eventId]);

  const handleFeedback = (idx, accepted) => {
    setFeedback({ ...feedback, [idx]: accepted ? 'accepted' : 'rejected' });
  };

  if (loading) return <div className="panel"><p className="text-muted">Generating recommendations...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;

  const sourceColors = {
    'risk_mitigation': '#f56565',
    'stabilization_driver': '#fbbf24',
    'correlation_model': '#63b3ed',
    'recipe_constraint': '#48bb78',
    'operator_pattern': '#a78bfa',
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">💡 Recommendations</h2>
          <p className="panel-subtitle">{recommendations.length} suggestions ranked by confidence</p>
        </div>
      </div>

      {recommendations.length === 0 ? (
        <p className="text-muted">No recommendations at this time.</p>
      ) : (
        <div className="recommendation-list">
          {recommendations.map((rec, idx) => (
            <div key={idx} style={{
              marginBottom: '1rem',
              padding: '1rem',
              background: '#2d3748',
              borderLeft: `4px solid ${sourceColors[rec.source_tag] || '#63b3ed'}`,
              borderRadius: '6px',
              borderBottom: '1px solid #4a5568',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
                <div>
                  <h4 style={{ margin: '0 0 0.25rem 0', color: '#e2e8f0', fontSize: '1rem' }}>
                    {rec.variable.toUpperCase()}
                  </h4>
                  <div style={{ fontSize: '0.85rem', color: '#cbd5e0' }}>
                    {rec.current_value.toFixed(2)} → {rec.recommended_value.toFixed(2)}
                  </div>
                </div>
                <span style={{
                  background: sourceColors[rec.source_tag] || '#63b3ed',
                  color: '#1a202c',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: '600',
                }}>
                  {rec.source_tag.replace(/_/g, ' ').toUpperCase()}
                </span>
              </div>

              <p style={{ margin: '0.5rem 0', fontSize: '0.9rem', color: '#cbd5e0' }}>
                <strong>Effect:</strong> {rec.expected_effect}
              </p>
              <p style={{ margin: '0.5rem 0', fontSize: '0.85rem', color: '#a0aec0' }}>
                {rec.rationale}
              </p>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                <div style={{ flex: 1, background: '#1a202c', borderRadius: '4px', height: '4px', overflow: 'hidden' }}>
                  <div style={{
                    background: sourceColors[rec.source_tag] || '#63b3ed',
                    height: '100%',
                    width: `${rec.confidence * 100}%`,
                  }} />
                </div>
                <span style={{ fontSize: '0.75rem', color: '#a0aec0' }}>
                  {(rec.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>

              {!feedback[idx] && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <button
                    className="btn-accept"
                    onClick={() => handleFeedback(idx, true)}
                  >
                    ✓ Accept
                  </button>
                  <button
                    className="btn-reject"
                    onClick={() => handleFeedback(idx, false)}
                  >
                    ✗ Reject
                  </button>
                </div>
              )}
              {feedback[idx] && (
                <div style={{
                  marginTop: '0.75rem',
                  padding: '0.5rem',
                  background: feedback[idx] === 'accepted' ? '#1a3a1a' : '#3a1a1a',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  color: feedback[idx] === 'accepted' ? '#48bb78' : '#f56565',
                }}>
                  {feedback[idx] === 'accepted' ? '✓ Recommendation accepted' : '✗ Recommendation rejected'}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RecommendationFeed;
