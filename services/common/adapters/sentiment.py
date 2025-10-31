import datetime as dt
import requests
import random
import logging
from typing import List, Dict, Optional
from functools import lru_cache

# Externalize keywords to lists
KEYWORDS = [
    "liquidation", "margin call", "rekt", "funding", "open interest",
    "crash", "rally"
]

POSITIVE_WORDS = ["rally", "surge", "bull", "up", "green", "gain"]
NEGATIVE_WORDS = ["crash", "drop", "bear", "down", "red", "loss", "liquidat"]

@lru_cache(maxsize=128)
def fetch_sentiment_cryptopanic(api_key: Optional[str] = None) -> List[Dict]:
    """Fetch real sentiment from CryptoPanic API, fallback to mock data."""
    if not api_key:
        return fetch_sentiment_mock("global")

    try:
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            'auth_token': api_key,
            'public': 'true',
            'kind': 'news',
            'filter': 'important'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        posts = data.get('results', [])

        mentions = len(posts)
        score = 0
        keyword_counts = {k: 0 for k in KEYWORDS}

        for post in posts:
            title = post.get('title', '').lower()
            # Count keywords
            for keyword in KEYWORDS:
                if keyword in title:
                    keyword_counts[keyword] += 1
            # Simple sentiment scoring
            for word in POSITIVE_WORDS:
                if word in title:
                    score += 1
            for word in NEGATIVE_WORDS:
                if word in title:
                    score -= 1

        normalized_score = score / max(mentions, 1)  # Avoid division by zero

        return [{
            "timestamp": dt.datetime.utcnow().isoformat(),
            "mentions": mentions,
            "sentiment_score": normalized_score,
            "keyword_counts": keyword_counts
        }]

    except Exception as e:
        logging.error(f"Error fetching sentiment from CryptoPanic: {e}")
        return fetch_sentiment_mock("global")

def fetch_sentiment_mock(pair: str) -> List[Dict]:
    """Generate mock sentiment data."""
    mentions = random.randint(0, 20)
    sentiment_score = random.uniform(-1, 1)
    keyword_counts = {k: random.randint(0, 5) for k in KEYWORDS}

    return [{
        "timestamp": dt.datetime.utcnow().isoformat(),
        "mentions": mentions,
        "sentiment_score": sentiment_score,
        "keyword_counts": keyword_counts
    }]
