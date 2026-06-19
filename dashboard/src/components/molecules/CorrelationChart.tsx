'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PriceCorrelation } from '../../lib/data';

interface CorrelationChartProps {
  data: PriceCorrelation[];
}

const CorrelationChart: React.FC<CorrelationChartProps> = ({ data }) => {
  // Downsample to ~200 points for smooth rendering and high performance
  const sampleRate = Math.max(1, Math.floor(data.length / 200));
  const downsampledData = data.filter((_, index) => index % sampleRate === 0);

  // Format timestamp to date string
  const formatXAxis = (tickItem: number) => {
    return new Date(tickItem * 1000).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTooltipLabel = (label: number) => {
    return new Date(label * 1000).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="card" style={{ height: '450px', width: '100%', marginBottom: '2rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <h3 className="accent-text" style={{ margin: 0 }}>BTC vs. Polymarket Contract Price Correlation</h3>
        <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
          Visualizing how YES contract pricing correlates with and anticipates short-term BTC price intervals.
        </p>
      </div>
      
      <ResponsiveContainer width="100%" height="80%">
        <LineChart data={downsampledData} margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          
          <XAxis 
            dataKey="timestamp" 
            tickFormatter={formatXAxis} 
            stroke="var(--muted)" 
            fontSize={11}
            tickLine={false}
          />
          
          <YAxis 
            yAxisId="left"
            domain={['auto', 'auto']}
            stroke="var(--accent)"
            fontSize={11}
            tickFormatter={(value) => `$${value.toLocaleString()}`}
            tickLine={false}
            axisLine={false}
          />
          
          <YAxis 
            yAxisId="right"
            orientation="right"
            domain={[0, 1]}
            stroke="var(--success)"
            fontSize={11}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
            tickLine={false}
            axisLine={false}
          />
          
          <Tooltip 
            labelFormatter={formatTooltipLabel}
            contentStyle={{ backgroundColor: '#1a1d23', border: '1px solid var(--card-border)', borderRadius: '8px' }}
            itemStyle={{ fontSize: '12px' }}
          />
          
          <Legend 
            verticalAlign="top" 
            height={36} 
            wrapperStyle={{ fontSize: '12px' }}
          />
          
          <Line 
            name="BTC Price (USD)"
            yAxisId="left"
            type="monotone" 
            dataKey="btc_price" 
            stroke="var(--accent)" 
            dot={false}
            strokeWidth={2}
          />
          
          <Line 
            name="YES Price (Polymarket)"
            yAxisId="right"
            type="monotone" 
            dataKey="yes_price" 
            stroke="var(--success)" 
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CorrelationChart;
