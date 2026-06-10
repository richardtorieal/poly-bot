import asyncio
import click
import pandas as pd
from src.utils.logger import logger
from src.security.config import get_settings
from src.security.safety import SafetyManager
from src.data.client import PolymarketClient
from src.data.news_client import NewsClient
from src.strategies.news_trigger import NewsTriggerStrategy
from src.strategies.rule_book import RuleBookStrategy
from src.strategies.btc_trend import BTCTrendStrategy

@click.group()
def cli():
    """Poly-Bot: High-Frequency Polymarket Trading System."""
    pass

@cli.command()
@click.option("--strategy", required=True, help="Strategy to run (news-trigger, rule-book, btc-trend)")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--json-output", is_flag=True, help="Output results in JSON format for agents")
@click.option("--polling-interval", default=60, help="Seconds between scans (0 for single pass)")
def run(strategy: str, debug: bool, json_output: bool, polling_interval: int):
    """Starts the bot with the specified strategy."""
    settings = get_settings()
    if debug:
        settings.DEBUG = True

    if not json_output:
        logger.info(f"Initializing Poly-Bot with strategy: {strategy}")
    safety = SafetyManager(settings)
    news_client = NewsClient()

    async def main():
        async with PolymarketClient(settings) as client:
            strat_inst = None
            if strategy == "news-trigger":
                strat_inst = NewsTriggerStrategy(client, safety, news_client)
            elif strategy == "rule-book":
                strat_inst = RuleBookStrategy(client, safety)
            elif strategy == "btc-trend":
                # For now, btc-trend is primarily handled via paper_trade_audit.py
                # but we keep the entry point here for future live parity.
                logger.warning("BTC Trend Live mode is under development. Use poly-bot-paper for simulation.")
                return
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

if __name__ == "__main__":
    cli()
