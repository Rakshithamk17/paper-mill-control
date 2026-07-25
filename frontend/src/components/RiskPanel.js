import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import api from '../api';

function RiskPanel({ eventId }) {
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;

    const fetchRisk = async () => {
      try {
        setLoading(true);
        const response = await api.post('/predict-risk', { event_id: eventId });
        setRisk(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to predict risk');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchRisk();
  }, [eventId]);

  if (loading) return <div className="panel"><p className="text-muted">Calculating risk...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;
  if (!risk) return <div className="panel"><p className="text-muted">No risk data</p></div>;

  const riskPercent = (risk.risk_probability * 100).toFixed(1);
  const riskColor = risk.risk_probability > 0.7 ? '#f56565' : risk.risk_probability > 0.4 ? '#ed8936' : '#48bb78';
  const riskLevel = risk.risk_probability > 0.7 ? 'HIGH' : risk.risk_probability > 0.4 ? 'MEDIUM' : 'LOW';

  const chartData = risk.top_risk_drivers?.map((driver, idx) => ({
    name: driver.feature.substring(0, 15),
    importance: driver.importance * 100,
  })) || [];

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">⚠️ Risk Assessment</h2>
          <p className="panel-subtitle">Basis Weight Deviation Risk</p>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <div style={{
          fontSize: '3rem',
          fontWeight: 'bold',
          color: riskColor,
          marginBottom: '0.5rem',
        }}>
          {riskPercent}%
        </div>
        <div style={{ fontSize: '1.25rem', color: riskColor, fontWeight: '600', marginBottom: '1rem' }}>
          {riskLevel} RISK
        </div>
        <div className="text-sm text-muted">
          {risk.will_breach ? '⚠️ Will breach ±2.5% band' : '✓ Likely within spec'}
        </div>
      </div>

      <div style={{ marginBottom: '1rem', borderTop: '1px solid #2d3748', paddingTop: '1rem' }}>
        <h3 style={{ fontSize: '0.95rem', color: '#cbd5e0', marginBottom: '0.75rem' }}>Top Risk Drivers:</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
            <XAxis dataKey="name" stroke="#a0aec0" tick={{ fontSize: 12 }} />
            <YAxis stroke="#a0aec0" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: '#2d3748', border: '1px solid #4a5568', borderRadius: '6px' }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={(value) => value.toFixed(1) + '%'}
            />
            <Bar dataKey="importance" fill="#f56565" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="text-xs text-muted">
        <p>🔍 These factors most influence breach probability. Monitor closely.</p>
      </div>
    </div>
  );
}

export default RiskPanel;
