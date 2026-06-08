import json
import os
import pandas as pd
from datetime import datetime

def generate_report(ledger_path="poly-bot/logs/paper_ledger.json"):
    if not os.path.exists(ledger_path):
        print("No ledger found yet. Waiting for first trade.")
        return

    with open(ledger_path, 'r') as f:
        data = json.load(f)
    
    history = data.get("history", [])
    if not history:
        print("No trade history in ledger.")
        return

    df = pd.DataFrame(history)
    df['t_entry'] = pd.to_datetime(df['t_entry'])
    df['date'] = df['t_entry'].dt.date

    print("\n" + "="*50)
    print(f"📈 sniper-V3 PERFORMANCE DASHBOARD")
    print("="*50)
    print(f"Current Balance: ${data.get('current_balance', 1000):,.2f}")
    print(f"Total Trades:    {len(df)}")
    print(f"Overall Win Rate: {(df['win'].mean()*100):.2f}%")
    print(f"Total PnL:       ${df['pnl'].sum():,.2f}")
    
    print("\n📅 PROFIT BY DAY:")
    daily = df.groupby('date')['pnl'].sum()
    for date, pnl in daily.items():
        print(f"  {date}: {'+$' if pnl>=0 else '-$'}{abs(pnl):.2f}")

    print("\n🏃 PROFIT BY RUN:")
    runs = df.groupby('run_id')['pnl'].agg(['sum', 'count'])
    for run_id, row in runs.iterrows():
        print(f"  {run_id}: {'+$' if row['sum']>=0 else '-$'}{abs(row['sum']):.2f} ({int(row['count'])} trades)")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    generate_report()
