import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../api';

function StabilizationDrivers({ eventId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;

    const fetchStabilization = async () => {
      try {
        setLoading(true);
        const response = await api.post('/predict-stabilization', { event_id: eventId });
        setData(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to predict stabilization');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchStabilization();
  }, [eventId]);

  if (loading) return <div className="panel"><p className="text-muted">Analyzing stabilization...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;
  if (!data) return <div className="panel"><p className="text-muted">No data available</p></div>;

  const stabTime = data.predicted_stabilization_sec;
  const drivers = data.stabilization_drivers || [];

  const chartData = drivers.map(d => ({
    name: d.variable.substring(0, 12),
    impact: d.impact_on_settling * 100,
  }));

  const stabTimeColor = stabTime < 300 ? '#48bb78' : stabTime < 450 ? '#ed8936' : '#f56565';

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">⚡ Stabilization Drivers</h2>
          <p className="panel-subtitle">Variables affecting settling time</p>
        </div>
      </div>

      <div style={{
        padding: '1rem',
        background: '#2d3748',
        borderRadius: '6px',
        marginBottom: '1.5rem',
        textAlign: 'center',
      }}>
        <div className="text-sm text-muted">Predicted Stabilization Time</div>
        <div style={{
          fontSize: '2rem',
          fontWeight: 'bold',
          color: stabTimeColor,
          marginTop: '0.5rem',
        }}>
          {stabTime.toFixed(0)} seconds
        </div>
        <div className="text-sm text-muted" style={{ marginTop: '0.5rem' }}>
          {stabTime < 300 && '✓ Fast settling'}
          {stabTime >= 300 && stabTime < 450 && '⚠️ Moderate settling'}
          {stabTime >= 450 && '🚨 Slow settling'}
        </div>
      </div>

      <h3 style={{ fontSize: '0.95rem', color: '#cbd5e0', marginBottom: '0.75rem' }}>Top Factors:</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="name" stroke="#a0aec0" tick={{ fontSize: 12 }} />
          <YAxis stroke="#a0aec0" tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ background: '#2d3748', border: '1px solid #4a5568', borderRadius: '6px' }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(value) => value.toFixed(1) + '%'}
          />
          <Bar dataKey="impact" fill="#fbbf24" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      <div className="text-xs text-muted" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #2d3748' }}>
        <p>💡 Adjust top factors to reduce settling time:</p>
        {drivers.slice(0, 2).map((d, i) => (
          <p key={i}>• {d.variable}: increase ramp rate by 10-20%</p>
        ))}
      </div>
    </div>
  );
}

export default StabilizationDrivers;
