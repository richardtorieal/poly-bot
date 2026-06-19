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
    sharpeRatio: number;
  };
}

const DATA_DIR = path.join(process.cwd(), 'data');
const INITIAL_BALANCE = 1000.0;
const TRADING_DAYS = 30.0;
const ANNUAL_TRADING_DAYS = 252.0;

export async function getDashboardData(): Promise<DashboardData> {
  const auditPath = path.join(DATA_DIR, 'real_sniper_30d_audit.csv');
  const correlationPath = path.join(DATA_DIR, 'btc_high_res_correlated_30d.csv');

  const auditContent = fs.readFileSync(auditPath, 'utf8');
  const correlationContent = fs.readFileSync(correlationPath, 'utf8');

  const auditResult = Papa.parse(auditContent, { header: true, dynamicTyping: true });
  const correlationResult = Papa.parse(correlationContent, { header: true, dynamicTyping: true });

  // Filter out any empty rows
  const trades = (auditResult.data as Trade[]).filter(t => t.time && t.balance !== undefined);
  const correlations = (correlationResult.data as PriceCorrelation[]).filter(c => c.timestamp && c.btc_price !== undefined);

  // Calculate Summary
  const totalPnL = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);
  const totalTrades = trades.length;
  const wins = trades.filter(t => t.result === 'WIN').length;
  const finalBalance = INITIAL_BALANCE + totalPnL;

  // Max Drawdown calculation
  let maxDrawdown = 0;
  let peak = -Infinity;
  for (const t of trades) {
    if (t.balance > peak) peak = t.balance;
    const dd = (peak - t.balance) / peak;
    if (dd > maxDrawdown) maxDrawdown = dd;
  }

  // Sharpe Ratio calculation (constant-base return to handle negative/zero balance safely)
  const returns = trades.map(t => (t.pnl || 0) / INITIAL_BALANCE);
  const meanReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) / returns.length;
  const stdReturn = Math.sqrt(variance);
  
  // Annualize Sharpe ratio based on historical frequency in 30 days
  const tradesPerDay = totalTrades / TRADING_DAYS;
  const annualFactor = ANNUAL_TRADING_DAYS * tradesPerDay;
  const sharpeRatio = stdReturn > 0 ? (meanReturn / stdReturn) * Math.sqrt(annualFactor) : 0;

  return {
    trades,
    correlations,
    summary: {
      totalPnL,
      winRate: totalTrades > 0 ? (wins / totalTrades) * 100 : 0,
      totalTrades,
      initialBalance: INITIAL_BALANCE,
      finalBalance,
      maxDrawdown: maxDrawdown * 100,
      sharpeRatio
    }
  };
}
