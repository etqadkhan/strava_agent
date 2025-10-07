#!/usr/bin/env python3
"""
Strava Agent - Main Entry Point

This module serves as the main entry point for the Strava Agent application.
It initializes logging, creates the Telegram bot instance, and starts the bot.

The bot provides AI-powered running coaching through Telegram, integrating with:
- Strava API for running data
- Google Gemini for AI analysis
- ChromaDB for vector storage
- LangGraph for workflow orchestration

Author: Etqad Khan
Version: 1.0.0
"""

import logging
import sys
from telegram_bot.bot import StravaBot


def setup_logging():
    """
    Configure logging for the application.

    Sets up logging to both file and console with appropriate formatting.
    Logs are written to 'bot.log' and also displayed in the console.
    """
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Set up logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # File handler - write logs to bot.log
            logging.FileHandler("bot.log"),
            # Console handler - display logs in terminal
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set specific logger levels for external libraries to reduce noise
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)


def main():
    """
    Main function to start the Strava Agent bot.

    This function:
    1. Sets up logging configuration
    2. Creates a StravaBot instance
    3. Starts the bot and keeps it running
    4. Handles graceful shutdown on keyboard interrupt
    """
    try:
        # Set up logging
        setup_logging()

        # Log application startup
        logging.info("🚀 Starting Strava Agent...")
        logging.info("📱 Initializing Telegram bot...")

        # Create and start the bot
        bot = StravaBot()
        logging.info("✅ Bot initialized successfully!")

        # Start the bot (this will run indefinitely)
        logging.info("🔄 Starting bot polling...")
        bot.run()

    except KeyboardInterrupt:
        # Handle graceful shutdown on Ctrl+C
        logging.info("🛑 Received shutdown signal...")
        logging.info("👋 Strava Agent stopped gracefully")

    except Exception as e:
        # Log any unexpected errors
        logging.error(f"❌ Unexpected error in main: {e}")
        raise


if __name__ == "__main__":
    # Entry point when script is run directly
    main()
