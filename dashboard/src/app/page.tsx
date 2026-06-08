import React from 'react';
import { getDashboardData } from '@/lib/data';
import MetricCard from '@/components/atoms/MetricCard';
import EquityChart from '@/components/molecules/EquityChart';
import TradeTable from '@/components/organisms/TradeTable';
import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const data = await getDashboardData();
  const { summary, trades } = data;

  return (
    <main>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.25rem' }} className="neon-text">Sniper-V3 Dashboard</h1>
          <p style={{ color: 'var(--muted)' }}>30-Day Real Data Backtest (May 5 - June 4, 2026)</p>
        </div>
        <div className="card" style={{ padding: '0.75rem 1.5rem', borderLeft: '4px solid var(--accent)' }}>
          <span style={{ fontSize: '0.875rem', color: 'var(--muted)' }}>Asset:</span>
          <strong style={{ marginLeft: '0.5rem' }}>Bitcoin (BTC/USD)</strong>
        </div>
      </div>

      <div className="dashboard-grid">
        <MetricCard 
          label="Total PnL" 
          value={`${summary.totalPnL >= 0 ? '+' : ''}$${summary.totalPnL.toFixed(2)}`} 
          color={summary.totalPnL >= 0 ? 'success' : 'danger'}
        />
        <MetricCard 
          label="Win Rate" 
          value={summary.winRate.toFixed(1)} 
          suffix="%"
          color="accent"
        />
        <MetricCard 
          label="Total Trades" 
          value={summary.totalTrades} 
          color="accent"
        />
        <MetricCard 
          label="Max Drawdown" 
          value={`-${summary.maxDrawdown.toFixed(1)}`} 
          suffix="%"
          color="danger"
        />
      </div>

      <EquityChart data={trades} />

      <TradeTable trades={trades} />
      
      <footer style={{ marginTop: '4rem', paddingBottom: '2rem', textAlign: 'center', color: 'var(--muted)', fontSize: '0.75rem' }}>
        Polymarket CLOB & Coinbase API High-Resolution Dataset
      </footer>
    </main>
  );
}
