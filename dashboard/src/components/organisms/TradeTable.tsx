import React from 'react';
import { Trade } from '../../lib/data';

interface TradeTableProps {
  trades: Trade[];
}

const TradeTable: React.FC<TradeTableProps> = ({ trades }) => {
  return (
    <div className="card" style={{ overflowX: 'auto' }}>
      <h3 className="accent-text">Detailed Trade Ledger</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--card-border)', color: 'var(--muted)' }}>
            <th style={{ padding: '1rem 0.5rem' }}>Time (UTC)</th>
            <th style={{ padding: '1rem 0.5rem' }}>Signal</th>
            <th style={{ padding: '1rem 0.5rem' }}>Actual</th>
            <th style={{ padding: '1rem 0.5rem' }}>Result</th>
            <th style={{ padding: '1rem 0.5rem' }}>Entry Price</th>
            <th style={{ padding: '1rem 0.5rem' }}>PnL</th>
            <th style={{ padding: '1rem 0.5rem' }}>Balance</th>
          </tr>
        </thead>
        <tbody>
          {trades.slice().reverse().map((trade, i) => (
            <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
              <td style={{ padding: '0.75rem 0.5rem' }}>{trade.time}</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>
                <span className={trade.signal === 'UP' ? 'success-text' : 'danger-text'}>
                  {trade.signal}
                </span>
              </td>
              <td style={{ padding: '0.75rem 0.5rem' }}>{trade.actual}</td>
              <td style={{ padding: '0.75rem 0.5rem' }}>
                <span className={trade.result === 'WIN' ? 'success-text' : 'danger-text'}>
                  {trade.result}
                </span>
              </td>
              <td style={{ padding: '0.75rem 0.5rem' }}>${trade.entry_price?.toFixed(3)}</td>
              <td style={{ padding: '0.75rem 0.5rem' }} className={trade.pnl >= 0 ? 'success-text' : 'danger-text'}>
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
              </td>
              <td style={{ padding: '0.75rem 0.5rem' }}>${trade.balance?.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TradeTable;
