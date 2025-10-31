import datetime as dt
import requests
import random
from typing import List, Dict

KEYWORDS = ["liquidation", "margin call", "rekt", "funding", "open interest", "crash", "rally"]

def fetch_sentiment_cryptopanic(api_key: str = None) -> List[Dict]:
    """Fetch real sentiment from CryptoPanic (free tier)"""
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
        data = response.json()
        
        posts = data.get('results', [])
        mentions = len(posts)
        
        # Simple sentiment analysis based on post titles
        positive_words = ['rally', 'surge', 'bull', 'up', 'green', 'gain']
        negative_words = ['crash', 'drop', 'bear', 'down', 'red', 'loss', 'liquidat']
        
        score = 0
        keyword_counts = {k: 0 for k in KEYWORDS}
        
        for post in posts:
            title = post.get('title', '').lower()
            # Count keywords
            for keyword in KEYWORDS:
                if keyword in title:
                    keyword_counts[keyword] += 1
            # Calculate sentiment
            if any(word in title for word in positive_words):
                score += 1
            if any(word in title for word in negative_words):
                score -= 1
        
        # Normalize score
        if mentions > 0:
            score_norm = score / mentions
        else:
            score_norm = 0
            
        now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
        return [{
            "pair": "global", 
            "ts": now, 
            "mentions": mentions, 
            "score_norm": score_norm, 
            "keywords": keyword_counts
        }]
        
    except Exception as e:
        print(f"CryptoPanic error: {e}")
        return fetch_sentiment_mock("global")

def fetch_sentiment_mock(exchange_pair: str):
    """Fallback mock sentiment"""
    now = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    mentions = random.randint(5, 50)
    score = random.uniform(-1, 1)
    kw_counts = {k: random.randint(0, mentions//2) for k in KEYWORDS}
    return [{
        "pair": exchange_pair, 
        "ts": now, 
        "mentions": mentions, 
        "score_norm": score, 
        "keywords": kw_counts
    }]

def fetch_sentiment(exchange_pair: str, api_key: str = None) -> List[Dict]:
    """Main sentiment function with real data fallback"""
    try:
        # Try real data first
        real_data = fetch_sentiment_cryptopanic(api_key)
        if real_data:
            # Convert global sentiment to pair-specific
            real_data[0]["pair"] = exchange_pair
            return real_data
    except Exception as e:
        print(f"Real sentiment failed, using mock: {e}")
    
    return fetch_sentiment_mock(exchange_pair)