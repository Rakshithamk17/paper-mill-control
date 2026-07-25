import React, { useState, useEffect } from 'react';
import api from '../api';

function CorrelationDiscovery({ eventId }) {
  const [correlations, setCorrelations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;

    const fetchCorrelations = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/correlations?event_id=${eventId}&min_threshold=0.4`);
        // Filter to show only novel correlations
        const novel = response.data.correlations.filter(c => c.is_known_loop === 0).slice(0, 8);
        setCorrelations(novel);
        setError(null);
      } catch (err) {
        setError('Failed to fetch correlations');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchCorrelations();
  }, [eventId]);

  if (loading) return <div className="panel"><p className="text-muted">Discovering correlations...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;

  const maxCorr = Math.max(...correlations.map(c => c.correlation_strength), 0);

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">🔗 Correlation Discovery</h2>
          <p className="panel-subtitle">Newly discovered variable relationships</p>
        </div>
      </div>

      {correlations.length === 0 ? (
        <p className="text-muted">No new correlations discovered in this event.</p>
      ) : (
        <div className="correlation-table">
          {correlations.map((corr, idx) => {
            const barWidth = (corr.correlation_strength / maxCorr) * 100;
            return (
              <div key={idx} className="correlation-row" style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #2d3748' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: '600', color: '#63b3ed' }}>
                    {corr.var1} ↔ {corr.var2}
                  </span>
                  <span className="text-info">{(corr.correlation_strength * 100).toFixed(0)}%</span>
                </div>
                <div style={{
                  background: '#2d3748',
                  borderRadius: '4px',
                  height: '8px',
                  marginBottom: '0.5rem',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    background: `linear-gradient(90deg, #63b3ed, #2b6cb0)`,
                    height: '100%',
                    width: `${barWidth}%`,
                    transition: 'width 0.3s',
                  }} />
                </div>
                <p className="text-sm text-muted" style={{ margin: '0.25rem 0' }}>
                  {corr.var1} impact: {corr.var2 === 'basis_weight' ? 'on BW' : 'indirect'}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <div className="text-xs text-muted" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #2d3748' }}>
        <p>💡 These relationships are NOT in the known control loops. Use for fine-tuning.</p>
      </div>
    </div>
  );
}

export default CorrelationDiscovery;
