import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../api';

function LiveTrajectory({ eventId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;

    const fetchTrajectory = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/trajectory/${eventId}`);
        setData(response.data);
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

  if (loading) return <div className="panel"><p className="text-muted">Loading trajectory...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;
  if (!data) return <div className="panel"><p className="text-muted">No data available</p></div>;

  const target = data.target_basis_weight;
  const upperBand = target * 1.025;
  const lowerBand = target * 0.975;

  // Format data for chart
  const chartData = data.trajectory.map((point, idx) => ({
    ...point,
    time: idx * 5, // 5 second resolution
    target: target,
    upperBand: upperBand,
    lowerBand: lowerBand,
  }));

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">📈 Live Trajectory</h2>
          <p className="panel-subtitle">Basis Weight vs. Target & ±2.5% Band</p>
        </div>
        <span className={`outcome-badge outcome-${data.outcome.toLowerCase()}`}>
          {data.outcome}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
          <XAxis dataKey="time" stroke="#a0aec0" label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -5 }} />
          <YAxis stroke="#a0aec0" label={{ value: 'Basis Weight (g/m²)', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{ background: '#2d3748', border: '1px solid #4a5568', borderRadius: '6px' }}
            labelStyle={{ color: '#e2e8f0' }}
          />
          <Legend wrapperStyle={{ color: '#cbd5e0' }} />
          <Line type="monotone" dataKey="basis_weight" stroke="#63b3ed" name="Actual" isAnimationActive={false} />
          <Line type="monotone" dataKey="target" stroke="#48bb78" name="Target" isAnimationActive={false} strokeDasharray="5 5" />
          <Line type="monotone" dataKey="upperBand" stroke="#f56565" name="Upper Band (+2.5%)" isAnimationActive={false} strokeDasharray="3 3" />
          <Line type="monotone" dataKey="lowerBand" stroke="#f56565" name="Lower Band (-2.5%)" isAnimationActive={false} strokeDasharray="3 3" />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-2">
        <div className="text-sm text-muted">
          <p>📊 Event: {eventId}</p>
          <p>🎯 Target: {target.toFixed(2)} g/m²</p>
          <p>📏 Band: {lowerBand.toFixed(2)} - {upperBand.toFixed(2)} g/m²</p>
        </div>
      </div>
    </div>
  );
}

export default LiveTrajectory;
