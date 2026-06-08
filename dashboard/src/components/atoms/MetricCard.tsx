import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'success' | 'danger' | 'accent';
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, suffix, trend, color }) => {
  return (
    <div className="card">
      <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>{label}</p>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
        <h2 className={`neon-text ${color ? color + '-text' : ''}`} style={{ fontSize: '1.75rem', margin: 0 }}>
          {value}
        </h2>
        {suffix && <span style={{ fontSize: '1rem', color: 'var(--muted)' }}>{suffix}</span>}
      </div>
    </div>
  );
};

export default MetricCard;
