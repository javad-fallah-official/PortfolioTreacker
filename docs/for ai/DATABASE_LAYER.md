# Database Layer - Detailed Documentation for AI

This document explains the database layer implemented in database.py.

## database.py

- Purpose: Provide a simple SQLite-based persistence for portfolio snapshots and asset balances.
- Imports: sqlite3, dataclasses/typing, datetime/time, json, pathlib, logging.

### Schema

- Table `portfolio_snapshots`:
  - `id` INTEGER PRIMARY KEY AUTOINCREMENT
  - `date` TEXT (ISO date 'YYYY-MM-DD') UNIQUE
  - `total_value_usd` REAL
  - `total_invested_usd` REAL
  - `total_profit_loss_usd` REAL
  - `btc_price_usd` REAL
  - `eth_price_usd` REAL
  - `notes` TEXT (optional)

- Table `asset_balances`:
  - `id` INTEGER PRIMARY KEY AUTOINCREMENT
  - `snapshot_id` INTEGER REFERENCES `portfolio_snapshots(id)` ON DELETE CASCADE
  - `currency` TEXT
  - `balance` REAL
  - `value_usd` REAL
  - `avg_buy_price_usd` REAL (optional)
  - `profit_loss_usd` REAL (optional)

### Class: PortfolioDatabase

- `__init__(db_path='portfolio.db')`:
  - Stores path and ensures parent directory exists.
  - Creates connection with `check_same_thread=False`; sets row factory to dict-like.
  - Calls `_init_db()` to create tables if not exists and enforce PRAGMA settings (foreign keys on, journal_mode=WAL optional).

- `_init_db()`:
  - Executes CREATE TABLE IF NOT EXISTS for both tables.
  - Creates indexes: `idx_portfolio_date`, `idx_asset_snapshot`, `idx_asset_currency`.

- `save_daily_portfolio(date, total_value_usd, total_invested_usd, btc_price_usd, eth_price_usd, assets, notes=None)`:
  - Inserts or REPLACE into `portfolio_snapshots` by date.
  - Retrieves `snapshot_id` (lastrowid or SELECT by date).
  - Deletes existing `asset_balances` for same `snapshot_id` to avoid duplicates.
  - Bulk inserts assets list: each item expects `currency`, `balance`, `value_usd`, optional `avg_buy_price_usd`, `profit_loss_usd`.
  - Returns snapshot_id.

- `get_historical_portfolio(start_date=None, end_date=None)`:
  - SELECTs snapshots between dates (if given) ordered ascending.
  - Returns list of dict rows.

- `get_asset_balances(snapshot_id=None, currency=None)`:
  - If `snapshot_id` provided: filters by snapshot.
  - If `currency` provided: filters by currency.
  - Joins as needed to snapshot table for date, when returning time-series per currency.

- `get_latest_snapshot()`:
  - SELECTs max(date) snapshot and returns dict with snapshot and balances for that day.

- `get_portfolio_stats(days=None)`:
  - Computes total number of snapshots, min/max dates, latest total value/invested/profit.
  - If `days` provided: also computes change over the period and average daily change.

- `compare_coin_performance(days=30)`:
  - For each currency with data in the last N days: compute change in `value_usd` and `balance` from first to last snapshot within window.
  - Returns sorted list by P/L descending.

- `close()`:
  - Closes the connection safely.

### Usage Notes

- All methods use parameterized queries to avoid SQL injection.
- Dates are stored as TEXT for easier filtering and index usage; convert to datetime in app layer as needed.
- For bulk operations, `executemany` is used for performance.
- Consider wrapping save operations in explicit transactions for larger imports.

### Extension Ideas

- Add table for transactions/trades for more granular P/L.
- Add views or materialized summaries for faster dashboard queries.
- Migrate to SQLAlchemy for more complex querying if needed.