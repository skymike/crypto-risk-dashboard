import os, psycopg2, pandas as pd
from psycopg2.extras import execute_values

def _conn():
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        host=_cfg.pg_host, port=_cfg.pg_port, dbname=_cfg.pg_db,
        user=_cfg.pg_user, password=_cfg.pg_pass
    # fallback to local docker compose
    host = os.getenv("POSTGRES_HOST","db")
    port = int(os.getenv("POSTGRES_PORT","5432"))
    db   = os.getenv("POSTGRES_DB","cryptodb")
    user = os.getenv("POSTGRES_USER","cryptouser")
    pwd  = os.getenv("POSTGRES_PASSWORD","cryptopass")
    return psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)

def execute(sql, params=None):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params or {})

def fetch_df(sql, params=None) -> pd.DataFrame:
    with _conn() as conn:
        return pd.read_sql(sql, conn, params=params)

def upsert_many(table: str, rows: list[dict], conflict_cols: list[str], update_cols: list[str]):
    if not rows: return
    cols = list(rows[0].keys())
    vals = [[r[c] for c in cols] for r in rows]
    on_conflict = ", ".join(conflict_cols)
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in update_cols])
    sql = f"""
    INSERT INTO {table} ({",".join(cols)})
    VALUES %s
    ON CONFLICT ({on_conflict}) DO UPDATE SET {updates}
    """
    with _conn() as conn, conn.cursor() as cur:
        execute_values(cur, sql, vals)

def ensure_schema():
    from services_common.schema import SCHEMA_SQL
    execute(SCHEMA_SQL)
    try:
        from pathlib import Path
        ts_sql = (Path(__file__).parent / "schema_timescale.sql")
        if ts_sql.exists():
            with _conn() as conn, conn.cursor() as cur:
                cur.execute(ts_sql.read_text(encoding="utf-8"))
    except Exception:
        pass
