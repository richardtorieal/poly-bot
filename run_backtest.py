import asyncio
import click
import pandas as pd
from src.data.historical import HistoricalDownloader
from src.utils.backtest_engine import BacktestEngine
from src.utils.logger import logger

async def run_logic(slug):
    logger.info(f"🚀 Starting Baseline Backtest for market: {slug}")
    downloader = HistoricalDownloader()
    engine = BacktestEngine()

    try:
        market = await downloader.get_market_metadata(slug)
        if not market:
            logger.error(f"Market slug '{slug}' not found.")
            return

        clob_ids = market.get("clobTokenIds", [])
        logger.info(f"Found {len(clob_ids)} outcomes. Downloading history...")

        data_frames = []
        for token_id in clob_ids:
            df = await downloader.fetch_price_history(token_id, interval="1w")
            if not df.empty:
                data_frames.append(df)

        if not data_frames:
            logger.error("Failed to download any historical data.")
            return

        # Run Simulation with 0.5% margin to catch more data
        results = engine.simulate_negative_risk(data_frames, margin_threshold=0.005)
        
        logger.warning("📊 BACKTEST RESULTS:")
        logger.info(f"Initial Balance: ${results['initial_balance']:.2f}")
        logger.info(f"Final Balance:   ${results['final_balance']:.2f}")
        logger.info(f"Total PnL:       ${results['total_pnl']:.2f}")
        logger.info(f"Total Trades:    {results['total_trades']}")
        logger.info(f"Bundle Price Range: [{results['min_bundle_price']:.4f} - {results['max_bundle_price']:.4f}]")

        logger.warning("🤖 STARTING AUTO-TUNING...")
        best_params = engine.auto_tune_negative_risk(data_frames)
        logger.warning(f"✅ OPTIMAL PARAMETERS: {best_params}")

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
    finally:
        await downloader.close()

@click.command()
@click.option("--slug", default="presidential-election-winner-2024", help="Market slug to backtest")
def main(slug):
    asyncio.run(run_logic(slug))

if __name__ == "__main__":
    main()
