'use client';

import React, { useState } from 'react';
import { Trade } from '../../lib/data';
import { Filter, ArrowUpDown } from 'lucide-react';

interface TradeTableProps {
  trades: Trade[];
}

const TradeTable: React.FC<TradeTableProps> = ({ trades }) => {
  const [signalFilter, setSignalFilter] = useState<'ALL' | 'UP' | 'DOWN'>('ALL');
  const [resultFilter, setResultFilter] = useState<'ALL' | 'WIN' | 'LOSS'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Filter trades based on state
  const filteredTrades = trades.filter(t => {
    const matchesSignal = signalFilter === 'ALL' || t.signal === signalFilter;
    const matchesResult = resultFilter === 'ALL' || t.result === resultFilter;
    const matchesSearch = t.time.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          t.actual.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSignal && matchesResult && matchesSearch;
  });

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h3 className="accent-text" style={{ margin: 0 }}>Detailed Trade Ledger</h3>
          <p style={{ color: 'var(--muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Showing {filteredTrades.length} of {trades.length} executed transaction entries.
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '0.375rem 0.75rem', borderRadius: '0.5rem', border: '1px solid var(--card-border)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Filter size={12} /> Signal:
            </span>
            <select 
              value={signalFilter} 
              onChange={(e) => setSignalFilter(e.target.value as any)}
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.75rem', cursor: 'pointer', outline: 'none' }}
            >
              <option value="ALL" style={{ background: '#1a1d23' }}>All Signals</option>
              <option value="UP" style={{ background: '#1a1d23' }}>UP Only</option>
              <option value="DOWN" style={{ background: '#1a1d23' }}>DOWN Only</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '0.375rem 0.75rem', borderRadius: '0.5rem', border: '1px solid var(--card-border)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Filter size={12} /> Outcome:
            </span>
            <select 
              value={resultFilter} 
              onChange={(e) => setResultFilter(e.target.value as any)}
              style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.75rem', cursor: 'pointer', outline: 'none' }}
            >
              <option value="ALL" style={{ background: '#1a1d23' }}>All Results</option>
              <option value="WIN" style={{ background: '#1a1d23' }}>WIN Only</option>
              <option value="LOSS" style={{ background: '#1a1d23' }}>LOSS Only</option>
            </select>
          </div>

          <input 
            type="text" 
            placeholder="Search dates..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ 
              background: 'rgba(255,255,255,0.05)', 
              border: '1px solid var(--card-border)', 
              borderRadius: '0.5rem', 
              padding: '0.375rem 0.75rem', 
              color: '#fff', 
              fontSize: '0.75rem',
              outline: 'none',
              minWidth: '150px'
            }}
          />
        </div>
      </div>

      {/* Table Container */}
      <div style={{ overflowX: 'auto', maxHeight: '450px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '0.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem', textAlign: 'left' }}>
          <thead style={{ position: 'sticky', top: 0, backgroundColor: '#0f1115', borderBottom: '1px solid var(--card-border)', zIndex: 1 }}>
            <tr>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600 }}>Time (UTC)</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600 }}>Signal</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600 }}>Actual Outcome</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600 }}>Result</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600, textAlign: 'right' }}>Entry Price</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600, textAlign: 'right' }}>PnL</th>
              <th style={{ padding: '1rem', color: 'var(--muted)', fontWeight: 600, textAlign: 'right' }}>Balance</th>
            </tr>
          </thead>
          <tbody>
            {filteredTrades.slice().reverse().map((trade, i) => (
              <tr 
                key={i} 
                style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.02)',
                  transition: 'background-color 0.2s',
                  backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)'
                }}
                className="table-row-hover"
              >
                <td style={{ padding: '0.875rem 1rem', color: 'rgba(255,255,255,0.85)' }}>{trade.time}</td>
                <td style={{ padding: '0.875rem 1rem' }}>
                  <span 
                    style={{ 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '0.25rem', 
                      fontSize: '0.75rem', 
                      fontWeight: 600,
                      backgroundColor: trade.signal === 'UP' ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 77, 77, 0.1)',
                    }}
                    className={trade.signal === 'UP' ? 'success-text' : 'danger-text'}
                  >
                    {trade.signal}
                  </span>
                </td>
                <td style={{ padding: '0.875rem 1rem', color: 'rgba(255,255,255,0.85)' }}>{trade.actual}</td>
                <td style={{ padding: '0.875rem 1rem' }}>
                  <span 
                    style={{ 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '0.25rem', 
                      fontSize: '0.75rem', 
                      fontWeight: 600,
                      backgroundColor: trade.result === 'WIN' ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 77, 77, 0.1)',
                    }}
                    className={trade.result === 'WIN' ? 'success-text' : 'danger-text'}
                  >
                    {trade.result}
                  </span>
                </td>
                <td style={{ padding: '0.875rem 1rem', textAlign: 'right', color: 'rgba(255,255,255,0.85)' }}>
                  ${trade.entry_price?.toFixed(3)}
                </td>
                <td 
                  style={{ padding: '0.875rem 1rem', textAlign: 'right', fontWeight: 600 }} 
                  className={trade.pnl >= 0 ? 'success-text' : 'danger-text'}
                >
                  {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                </td>
                <td style={{ padding: '0.875rem 1rem', textAlign: 'right', fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>
                  ${trade.balance?.toFixed(2)}
                </td>
              </tr>
            ))}
            {filteredTrades.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: '3rem', textAlign: 'center', color: 'var(--muted)' }}>
                  No transaction entries found matching the active filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradeTable;
