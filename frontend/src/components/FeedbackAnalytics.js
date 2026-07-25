import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import api from '../api';

function FeedbackAnalytics() {
  const [analytics, setAnalytics] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const analyticsRes = await api.get('/feedback-analytics');
        const statsRes = await api.get('/stats');
        setAnalytics(analyticsRes.data);
        setStats(statsRes.data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch analytics');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  if (loading) return <div className="panel"><p className="text-muted">Loading analytics...</p></div>;
  if (error) return <div className="panel"><p className="text-danger">{error}</p></div>;
  if (!analytics || !stats) return <div className="panel"><p className="text-muted">No data available</p></div>;

  const feedbackData = [
    { name: 'Accepted', value: analytics.accepted, fill: '#48bb78' },
    { name: 'Rejected', value: analytics.rejected, fill: '#f56565' },
  ];

  const outcomeData = [
    { name: 'Success', value: stats.outcomes.SUCCESS || 0, fill: '#48bb78' },
    { name: 'Marginal', value: stats.outcomes.MARGINAL || 0, fill: '#ed8936' },
    { name: 'Off-Spec', value: stats.outcomes.OFF_SPEC || 0, fill: '#f56565' },
  ];

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">📊 Feedback Analytics</h2>
          <p className="panel-subtitle">Operator feedback and system performance metrics</p>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: '2rem' }}>
        {/* Recommendation Feedback */}
        <div>
          <h3 style={{ fontSize: '1rem', color: '#cbd5e0', marginBottom: '1rem' }}>Recommendation Acceptance Rate</h3>
          {analytics.total_recommendations > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={feedbackData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {feedbackData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ marginTop: '1rem', padding: '1rem', background: '#2d3748', borderRadius: '6px' }}>
                <p style={{ margin: '0 0 0.5rem 0' }}>📈 <strong>{(analytics.acceptance_rate * 100).toFixed(1)}%</strong> acceptance rate</p>
                <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem' }}>✓ {analytics.accepted} recommendations accepted</p>
                <p style={{ margin: '0', fontSize: '0.9rem' }}>✗ {analytics.rejected} recommendations rejected</p>
              </div>
            </>
          ) : (
            <p className="text-muted">No feedback recorded yet.</p>
          )}
        </div>

        {/* Grade Change Outcomes */}
        <div>
          <h3 style={{ fontSize: '1rem', color: '#cbd5e0', marginBottom: '1rem' }}>Grade Change Outcomes</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={outcomeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {outcomeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ marginTop: '1rem', padding: '1rem', background: '#2d3748', borderRadius: '6px' }}>
            <p style={{ margin: '0 0 0.25rem 0' }}>🎯 Success Rate: {(((stats.outcomes.SUCCESS || 0) / Object.values(stats.outcomes).reduce((a, b) => a + b, 0)) * 100).toFixed(1)}%</p>
            <p style={{ margin: '0 0 0.25rem 0', fontSize: '0.9rem' }}>Average deviation: {stats.avg_deviation_pct?.toFixed(2)}%</p>
            <p style={{ margin: '0', fontSize: '0.9rem' }}>Avg settling time: {stats.avg_stabilization_sec?.toFixed(0)}s</p>
          </div>
        </div>
      </div>

      <div style={{
        padding: '1.5rem',
        background: '#2d3748',
        borderRadius: '6px',
        borderLeft: '4px solid #63b3ed',
      }}>
        <h3 style={{ margin: '0 0 1rem 0', color: '#e2e8f0' }}>Key Insights</h3>
        <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#cbd5e0', lineHeight: '1.8' }}>
          <li>System has processed {Object.values(stats.outcomes).reduce((a, b) => a + b, 0)} grade changes</li>
          <li>Operator acceptance rate of {(analytics.acceptance_rate * 100).toFixed(1)}% indicates model reliability</li>
          <li>Average basis weight deviation of {stats.avg_deviation_pct?.toFixed(2)}% is typical for this mill</li>
          <li>Stabilization takes ~{stats.avg_stabilization_sec?.toFixed(0)} seconds on average</li>
        </ul>
      </div>
    </div>
  );
}

export default FeedbackAnalytics;
