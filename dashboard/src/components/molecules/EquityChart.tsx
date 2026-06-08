'use client';

import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EquityChartProps {
  data: any[];
}

const EquityChart: React.FC<EquityChartProps> = ({ data }) => {
  return (
    <div className="card" style={{ height: '400px', width: '100%', marginBottom: '2rem' }}>
      <h3 className="accent-text">Equity Curve (Account Balance)</h3>
      <ResponsiveContainer width="100%" height="90%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="var(--accent)" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="time" 
            hide 
          />
          <YAxis 
            domain={['auto', 'auto']} 
            stroke="var(--muted)" 
            fontSize={12}
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1a1d23', border: '1px solid var(--card-border)', borderRadius: '8px' }}
            itemStyle={{ color: 'var(--accent)' }}
            labelStyle={{ display: 'none' }}
          />
          <Area 
            type="monotone" 
            dataKey="balance" 
            stroke="var(--accent)" 
            fillOpacity={1} 
            fill="url(#colorBalance)" 
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EquityChart;
