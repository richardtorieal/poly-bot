import React from 'react';
import * as Icons from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  subtext?: string;
  iconName?: keyof typeof Icons;
  color?: 'success' | 'danger' | 'accent' | 'warning';
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, suffix, subtext, iconName, color }) => {
  const IconComponent = iconName ? Icons[iconName] as React.ComponentType<{ size?: number; className?: string }> : null;

  // Determine neon glow colors based on themes
  const colorMap = {
    success: { text: 'success-text', glow: 'rgba(0, 255, 136, 0.15)' },
    danger: { text: 'danger-text', glow: 'rgba(255, 77, 77, 0.15)' },
    accent: { text: 'accent-text', glow: 'rgba(0, 212, 255, 0.15)' },
    warning: { text: 'warning-text', glow: 'rgba(255, 170, 0, 0.15)' }
  };

  const currentColors = color ? colorMap[color] : { text: '', glow: 'rgba(255, 255, 255, 0.05)' };

  return (
    <div 
      className="card" 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'space-between',
        boxShadow: `0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 0 12px ${currentColors.glow}`
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', fontWeight: 500 }}>{label}</p>
        {IconComponent && (
          <div className={color ? color + '-text' : ''} style={{ opacity: 0.8 }}>
            <IconComponent size={20} />
          </div>
        )}
      </div>
      
      <div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
          <h2 className={`neon-text ${currentColors.text}`} style={{ fontSize: '2rem', margin: 0, fontWeight: 700 }}>
            {value}
          </h2>
          {suffix && <span style={{ fontSize: '1.125rem', color: 'var(--muted)', fontWeight: 500 }}>{suffix}</span>}
        </div>
        
        {subtext && (
          <p style={{ color: 'var(--muted)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
            {subtext}
          </p>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
