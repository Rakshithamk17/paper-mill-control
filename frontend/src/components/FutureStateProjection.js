import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../api';

function FutureStateProjection({ eventId }) {
  const [trajectory, setTrajectory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;

    const fetchTrajectory = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/trajectory/${eventId}`);
        setTrajectory(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to load trajectory');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchTrajectory();
  }, [eventId]);

  if (loading) return <div className="panel"><p className="text-muted">Loading projection...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;
  if (!trajectory) return <div className="panel"><p className="text-muted">No data available</p></div>;

  const target = trajectory.target_basis_weight;
  const data = trajectory.trajectory;
  const lastIdx = data.length - 1;
  const recent = data.slice(Math.max(0, lastIdx - 20));

  // Calculate trend
  const startVal = recent[0].basis_weight;
  const endVal = recent[recent.length - 1].basis_weight;
  const trend = endVal - startVal;
  const trendPercent = ((trend / target) * 100).toFixed(1);
  const trendDirection = trend > 0 ? '📈' : '📉';
  const trendColor = Math.abs(trend) < 1 ? '#48bb78' : Math.abs(trend) < 3 ? '#ed8936' : '#f56565';

  // Project 100 more points
  const projectionLength = 100;
  let projectedData = [...recent];
  for (let i = 0; i < projectionLength; i++) {
    const lastPoint = projectedData[projectedData.length - 1];
    const decay = Math.exp(-i / 50); // Exponential decay
    const nextBW = lastPoint.basis_weight + trend * decay * 0.1;
    projectedData.push({
      ...lastPoint,
      basis_weight: nextBW,
      time: lastPoint.time + 5,
      is_projection: true,
    });
  }

  const chartData = projectedData.map((p, idx) => ({
    ...p,
    time: idx * 5,
  }));

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">🔮 Future-State Projection</h2>
          <p className="panel-subtitle">If current trend continues...</p>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="time" stroke="#a0aec0" label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -5 }} />
          <YAxis stroke="#a0aec0" />
          <Tooltip
            contentStyle={{ background: '#2d3748', border: '1px solid #4a5568', borderRadius: '6px' }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Line type="monotone" dataKey="basis_weight" stroke="#63b3ed" name="Basis Weight" isAnimationActive={false} />
          <Line type="monotone" dataKey="target" stroke="#48bb78" name="Target" strokeDasharray="5 5" isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>

      <div style={{
        marginTop: '1rem',
        padding: '1rem',
        background: '#2d3748',
        borderRadius: '6px',
        borderLeft: `4px solid ${trendColor}`,
      }}>
        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          {trendDirection} Current Trend: {trendPercent}% deviation/minute
        </div>
        <div className="text-sm text-muted">
          {Math.abs(trend) < 1 && '✓ Trend is stable - system settling normally'}
          {Math.abs(trend) >= 1 && Math.abs(trend) < 3 && '⚠️ Moderate drift detected - monitor closely'}
          {Math.abs(trend) >= 3 && '🚨 Strong drift - corrective action recommended'}
        </div>
      </div>
    </div>
  );
}

export default FutureStateProjection;
