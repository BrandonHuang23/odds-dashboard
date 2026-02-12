"""
Configuration loader for the Odds Dashboard backend.

Loads the BoltOdds API key from .env and defines API base URLs.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOLTODDS_API_KEY = os.environ.get("BOLTODDS_API_KEY", "")
BOLTODDS_REST_BASE = "https://spro.agency/api"
BOLTODDS_WS_URL = "wss://spro.agency/api"
