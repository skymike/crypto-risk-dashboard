import os
from dataclasses import dataclass

@dataclass
class Config:
    pg_user: str
    pg_pass: str
    pg_db: str
    pg_host: str
    pg_port: int
    redis_url: str
    symbols: list[str]

def load_config() -> Config:
    symbols_env = os.getenv("SYMBOLS", "binance:BTC/USDT")
    symbols = [s.strip() for s in symbols_env.split(",") if s.strip()]
    return Config(
        pg_user=os.getenv("POSTGRES_USER","cryptouser"),
        pg_pass=os.getenv("POSTGRES_PASSWORD","cryptopass"),
        pg_db=os.getenv("POSTGRES_DB","cryptodb"),
        pg_host=os.getenv("POSTGRES_HOST","db"),
        pg_port=int(os.getenv("POSTGRES_PORT","5432")),
        redis_url=os.getenv("REDIS_URL","redis://redis:6379/0"),
        symbols=symbols
    )
