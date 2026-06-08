import asyncio
import click
import pandas as pd
from src.utils.logger import logger
from src.security.config import get_settings
from src.security.safety import SafetyManager
from src.data.client import PolymarketClient
from src.data.news_client import NewsClient
from src.strategies.negative_risk import NegativeRiskStrategy
from src.strategies.news_trigger import NewsTriggerStrategy
from src.strategies.rule_book import RuleBookStrategy

@click.group()
def cli():
    """Poly-Bot: High-Frequency Polymarket Trading System."""
    pass

@cli.command()
@click.option("--strategy", required=True, help="Strategy to run (negative-risk, news-trigger, rule-book)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--json-output", is_flag=True, help="Output results in JSON format for agents")
@click.option("--polling-interval", default=60, help="Seconds between scans (0 for single pass)")
@click.option("--margin-threshold", default=0.02, help="Minimum profit margin (e.g. 0.0167 for 1.67%)")
def run(strategy: str, debug: bool, json_output: bool, polling_interval: int, margin_threshold: float):
    """Starts the bot with the specified strategy."""
    settings = get_settings()
    if debug:
        settings.DEBUG = True

    if not json_output:
        logger.info(f"Initializing Poly-Bot with strategy: {strategy} (Margin: {margin_threshold*100:.2f}%)")
    safety = SafetyManager(settings)
    news_client = NewsClient()

    async def main():
        async with PolymarketClient(settings) as client:
            strat_inst = None
            if strategy == "negative-risk":
                strat_inst = NegativeRiskStrategy(client, safety, polling_interval=polling_interval, profit_margin=margin_threshold)
            elif strategy == "news-trigger":
                strat_inst = NewsTriggerStrategy(client, safety, news_client)
            elif strategy == "rule-book":
                strat_inst = RuleBookStrategy(client, safety)
            else:
                if json_output:
                    print('{"error": "Unknown strategy"}')
                else:
                    logger.error(f"Unknown strategy: {strategy}")
                return

            if strat_inst:
                try:
                    await strat_inst.start()
                finally:
                    await news_client.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Poly-Bot shut down by user.")

@cli.command()
@click.option("--slug", default="will-harvey-weinstein-be-sentenced-to-between-20-and-30-years-in-prison", help="Market to optimize")
def optimize(slug: str):
    """Re-runs backtests and updates PM2 with optimal margin."""
    import subprocess
    from src.data.historical import HistoricalDownloader
    from src.utils.backtest_engine import BacktestEngine
    
    async def run_opt():
        logger.info(f"🔄 Starting Daily Optimization for {slug}...")
        downloader = HistoricalDownloader()
        engine = BacktestEngine()
        
        # 1. Fetch live data
        market = await downloader.get_market_metadata(slug)
        clob_ids = market.get("clobTokenIds", [])
        data_frames = []
        for tid in clob_ids:
            df = await downloader.fetch_price_history(tid, interval="all")
            if not df.empty: data_frames.append(df[['p']].rename(columns={'p': tid}))
        
        # 2. Find best margin
        best = engine.auto_tune_negative_risk([pd.concat(data_frames, axis=1).ffill().dropna()[[c]].rename(columns={c:'p'}) for c in clob_ids])
        new_margin = best['margin_threshold']
        
        logger.warning(f"✅ New Optimal Margin Found: {new_margin*100:.2f}%")
        
        # 3. Update PM2 Live
        cmd = f"pm2 restart poly-bot -- run --strategy negative-risk --margin-threshold {new_margin}"
        subprocess.run(cmd, shell=True)
        logger.info("🚀 PM2 Process updated and restarted with new margin.")
        await downloader.close()

    asyncio.run(run_opt())

if __name__ == "__main__":
    cli()
