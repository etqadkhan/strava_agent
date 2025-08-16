"""
Configuration Management for Strava Agent

This module handles all configuration settings for the Strava Agent application.
It loads environment variables from a .env file and provides centralized access
to configuration values throughout the application.

Environment Variables Required:
- STRAVA_CLIENT_ID: Your Strava application client ID
- STRAVA_CLIENT_SECRET: Your Strava application client secret
- STRAVA_REFRESH_TOKEN: Your Strava refresh token
- GOOGLE_API_KEY: Your Google Gemini API key
- TELEGRAM_TOKEN: Your Telegram bot token
- USERS: JSON string containing user configurations

Author: Etqad Khan
Version: 1.0.0
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This must be called before accessing any environment variables
load_dotenv()

# =============================================================================
# Strava API Configuration
# =============================================================================
# These are the global Strava credentials used as fallbacks
# User-specific credentials are stored in the USERS JSON
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# =============================================================================
# Google Gemini AI Configuration
# =============================================================================
# API key for Google's Gemini AI model
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model names for different AI tasks
# MODEL_NAME: Used for text generation and analysis
# EMBED_MODEL: Used for creating vector embeddings
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/text-embedding-004")

# =============================================================================
# Telegram Bot Configuration
# =============================================================================
# Token for your Telegram bot (obtained from @BotFather)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# =============================================================================
# Database Configuration
# =============================================================================
# Directory where ChromaDB stores vector embeddings
# Defaults to "./chroma_stores" relative to the application root
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_stores")

# =============================================================================
# User Configuration
# =============================================================================
# JSON string containing user-specific configurations
# Format: {"username": {"chat_id": "123", "strava_refresh_token": "token"}}
USERS_JSON = os.getenv("USERS")

# Parse the USERS JSON string into a Python dictionary
# This enables multi-user support with different Strava accounts
try:
    import json

    USERS = json.loads(USERS_JSON) if USERS_JSON else {}
except json.JSONDecodeError:
    # If JSON parsing fails, use empty dictionary
    # This prevents the application from crashing on invalid JSON
    USERS = {}
