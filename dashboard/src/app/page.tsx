import React from 'react';
import { getDashboardData } from '@/lib/data';
import MetricCard from '@/components/atoms/MetricCard';
import EquityChart from '@/components/molecules/EquityChart';
import CorrelationChart from '@/components/molecules/CorrelationChart';
import TradeTable from '@/components/organisms/TradeTable';
import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const data = await getDashboardData();
  const { summary, trades, correlations } = data;

  const pnlPct = (summary.totalPnL / summary.initialBalance) * 100;

  return (
    <main>
      {/* Header section */}
      <div 
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: '3rem',
          flexWrap: 'wrap',
          gap: '1.5rem'
        }}
      >
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.25rem', fontWeight: 700 }} className="neon-text">
            Sniper-V3 Dashboard
          </h1>
          <p style={{ color: 'var(--muted)', fontSize: '0.95rem' }}>
            30-Day Real Data Backtest (May 5 - June 4, 2026)
          </p>
        </div>
        <div 
          className="card" 
          style={{ 
            padding: '0.75rem 1.5rem', 
            borderLeft: '4px solid var(--accent)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            margin: 0
          }}
        >
          <span style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>Asset Class:</span>
          <strong style={{ fontSize: '0.95rem', color: '#fff' }}>Bitcoin (BTC/USD)</strong>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="dashboard-grid">
        <MetricCard 
          label="Total PnL" 
          value={`${summary.totalPnL >= 0 ? '+' : ''}$${summary.totalPnL.toFixed(2)}`}
          suffix=""
          subtext={`${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}% Return on capital`}
          iconName="DollarSign"
          color={summary.totalPnL >= 0 ? 'success' : 'danger'}
        />
        <MetricCard 
          label="Win Rate" 
          value={summary.winRate.toFixed(1)} 
          suffix="%"
          subtext="Percentage of winning intervals"
          iconName="Percent"
          color="success"
        />
        <MetricCard 
          label="Trade Volume" 
          value={summary.totalTrades} 
          subtext="Total executed contract orders"
          iconName="BarChart3"
          color="accent"
        />
        <MetricCard 
          label="Sharpe Ratio (est)" 
          value={summary.sharpeRatio.toFixed(2)} 
          subtext="Annualized risk-adjusted performance"
          iconName="Activity"
          color="accent"
        />
        <MetricCard 
          label="Max Drawdown" 
          value={`-${summary.maxDrawdown.toFixed(1)}`} 
          suffix="%"
          subtext="Peak-to-trough account drawdown"
          iconName="ShieldCheck"
          color="danger"
        />
      </div>

      {/* Equity Curve Chart */}
      <EquityChart data={trades} />

      {/* Correlation Chart */}
      <CorrelationChart data={correlations} />

      {/* Detailed Trade Ledger */}
      <TradeTable trades={trades} />
      
      <footer 
        style={{ 
          marginTop: '5rem', 
          paddingBottom: '2.5rem', 
          textAlign: 'center', 
          color: 'var(--muted)', 
          fontSize: '0.8rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          paddingTop: '2.5rem'
        }}
      >
        Polymarket CLOB & Coinbase API High-Resolution Dataset • Built with Next.js 15
      </footer>
    </main>
  );
}
