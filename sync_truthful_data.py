import pandas as pd
import asyncio
from src.data.historical import HistoricalDownloader
from src.utils.logger import logger
import os

async def sync():
    """
    Simulated sync: In a real environment, this would fetch the last 24h 
    and append to the CSV. For now, it verifies the 'Golden Dataset'.
    """
    path = "data/btc_truthful_1m_30d.csv"
    if not os.path.exists(path):
        logger.error(f"FATAL: {path} not found. System cannot start.")
        return

    df = pd.read_csv(path)
    logger.info(f"✅ Golden Dataset Verified: {len(df)} rows found.")
    logger.info(f"Last timestamp: {df['timestamp'].iloc[-1]}")

if __name__ == "__main__":
    asyncio.run(sync())
