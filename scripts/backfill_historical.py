"""One-time script to backfill 60 days of historical data."""
import sys
import logging
from datetime import datetime

# Reuse extract_data logic
from extract_data import main, logger

if __name__ == "__main__":
    logger.info("Running historical backfill...")
    logger.info("This will fetch 60 days of data from Databricks")

    # The extract_data main function already handles 60 days
    main()

    logger.info("Historical backfill completed")
