-- Enable Timescale if available
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert base tables to hypertables
SELECT create_hypertable('candles', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('funding_rates', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('open_interest', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('volatility', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('sentiment', 'ts', if_not_exists => TRUE);
SELECT create_hypertable('signals', 'ts', if_not_exists => TRUE);

-- Example continuous aggregate for faster OHLC queries
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', ts) AS bucket,
  pair,
  first(open, ts)  AS o,
  max(high)        AS h,
  min(low)         AS l,
  last(close, ts)  AS c,
  sum(volume)      AS v
FROM candles
GROUP BY 1,2;

-- Auto-refresh policy
SELECT add_continuous_aggregate_policy(
  'candles_1h',
  start_offset => INTERVAL '3 days',
  end_offset   => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '15 minutes'
);
