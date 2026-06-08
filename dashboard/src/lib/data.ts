import fs from 'fs';
import path from 'path';
import Papa from 'papaparse';

export interface Trade {
  time: string;
  signal: string;
  actual: string;
  result: 'WIN' | 'LOSS';
  entry_price: number;
  pnl: number;
  balance: number;
}

export interface PriceCorrelation {
  timestamp: number;
  yes_price: number;
  no_price: number;
  question: string;
  btc_price: number;
}

export interface DashboardData {
  trades: Trade[];
  correlations: PriceCorrelation[];
  summary: {
    totalPnL: number;
    winRate: number;
    totalTrades: number;
    initialBalance: number;
    finalBalance: number;
    maxDrawdown: number;
  };
}

const DATA_DIR = path.join(process.cwd(), 'data');

export async function getDashboardData(): Promise<DashboardData> {
  const auditPath = path.join(DATA_DIR, 'real_sniper_30d_audit.csv');
  const correlationPath = path.join(DATA_DIR, 'btc_high_res_correlated_30d.csv');

  const auditContent = fs.readFileSync(auditPath, 'utf8');
  const correlationContent = fs.readFileSync(correlationPath, 'utf8');

  const auditResult = Papa.parse(auditContent, { header: true, dynamicTyping: true });
  const correlationResult = Papa.parse(correlationContent, { header: true, dynamicTyping: true });

  const trades = auditResult.data as Trade[];
  const correlations = correlationResult.data as PriceCorrelation[];

  // Calculate Summary
  const totalPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const totalTrades = trades.length;
  const wins = trades.filter(t => t.result === 'WIN').length;
  const initialBalance = 1000.0;
  const finalBalance = initialBalance + totalPnL;

  // Max Drawdown calculation
  let maxDrawdown = 0;
  let peak = -Infinity;
  for (const t of trades) {
    if (t.balance > peak) peak = t.balance;
    const dd = (peak - t.balance) / peak;
    if (dd > maxDrawdown) maxDrawdown = dd;
  }

  return {
    trades,
    correlations,
    summary: {
      totalPnL,
      winRate: (wins / totalTrades) * 100,
      totalTrades,
      initialBalance,
      finalBalance,
      maxDrawdown: maxDrawdown * 100
    }
  };
}
