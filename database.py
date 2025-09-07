"""
Database module for portfolio tracking
Handles PostgreSQL operations for storing daily portfolio snapshots using asyncpg
"""

import os
import json
from datetime import datetime, date
from typing import Dict, List, Optional
from pathlib import Path
import logging
import asyncio

import asyncpg
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioDatabase:
    """Handles portfolio data storage and retrieval (async, PostgreSQL)"""

    def __init__(self, dsn: Optional[str] = None):
        """Prepare DSN from environment if not provided.
        Expected env vars: POSTGRES_DSN or POSTGRES_{HOST,PORT,USER,PASSWORD,DB}
        """
        self.dsn = dsn or os.getenv("POSTGRES_DSN") or self._build_dsn_from_env()
        if not self.dsn:
            # Provide a helpful hint
            raise ValueError(
                "PostgreSQL DSN is not configured. Set POSTGRES_DSN or POSTGRES_HOST/PORT/USER/PASSWORD/DB in environment."
            )
        self.pool: Optional[asyncpg.Pool] = None
        # run init lazily; user must call await init()

    @staticmethod
    def _build_dsn_from_env() -> Optional[str]:
        host = os.getenv("POSTGRES_HOST")
        db = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        port = os.getenv("POSTGRES_PORT", "5432")
        if host and db and user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return None

    async def init(self):
        """Create connection pool and ensure schema exists."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(dsn=self.dsn, min_size=1, max_size=10)
            await self._init_schema()
            logger.info("PostgreSQL pool initialized and schema ensured")

    async def _init_schema(self):
        create_snapshots = """
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL UNIQUE,
            timestamp TIMESTAMP NOT NULL,
            total_usd_value DOUBLE PRECISION NOT NULL,
            total_irr_value DOUBLE PRECISION NOT NULL,
            total_assets INTEGER NOT NULL,
            assets_with_balance INTEGER NOT NULL,
            account_email TEXT,
            account_user_id TEXT,
            raw_data JSONB NOT NULL
        );
        """

        create_asset_balances = """
        CREATE TABLE IF NOT EXISTS asset_balances (
            id SERIAL PRIMARY KEY,
            snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots (id) ON DELETE CASCADE,
            asset_name TEXT NOT NULL,
            asset_fa_name TEXT,
            free_amount DOUBLE PRECISION NOT NULL,
            total_amount DOUBLE PRECISION NOT NULL,
            usd_value DOUBLE PRECISION NOT NULL,
            irr_value DOUBLE PRECISION NOT NULL,
            has_balance BOOLEAN NOT NULL,
            is_fiat BOOLEAN DEFAULT FALSE,
            is_digital_gold BOOLEAN DEFAULT FALSE
        );
        """

        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_portfolio_date ON portfolio_snapshots(date);",
            "CREATE INDEX IF NOT EXISTS idx_asset_snapshot ON asset_balances(snapshot_id, asset_name);",
        ]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(create_snapshots)
                await conn.execute(create_asset_balances)
                for stmt in create_indexes:
                    await conn.execute(stmt)

    async def save_portfolio_snapshot(self, portfolio_data: Dict) -> bool:
        """Save a daily portfolio snapshot to the database (upsert by date)."""
        today = date.today()
        timestamp = datetime.now()

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Upsert into portfolio_snapshots by unique(date)
                    insert_snapshot = """
                    INSERT INTO portfolio_snapshots (
                        date, timestamp, total_usd_value, total_irr_value,
                        total_assets, assets_with_balance, account_email,
                        account_user_id, raw_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (date) DO UPDATE SET
                        timestamp = EXCLUDED.timestamp,
                        total_usd_value = EXCLUDED.total_usd_value,
                        total_irr_value = EXCLUDED.total_irr_value,
                        total_assets = EXCLUDED.total_assets,
                        assets_with_balance = EXCLUDED.assets_with_balance,
                        account_email = EXCLUDED.account_email,
                        account_user_id = EXCLUDED.account_user_id,
                        raw_data = EXCLUDED.raw_data
                    RETURNING id;
                    """
                    snapshot_row = await conn.fetchrow(
                        insert_snapshot,
                        today,
                        timestamp,
                        float(portfolio_data['balances']['total_usd_value']),
                        float(portfolio_data['balances']['total_irr_value']),
                        int(portfolio_data['balances']['total_assets']),
                        int(portfolio_data['balances']['assets_with_balance']),
                        portfolio_data['account'].get('email'),
                        str(portfolio_data['account'].get('user_id')),
                        json.dumps(portfolio_data),
                    )
                    snapshot_id = snapshot_row[0]

                    # Clean previous asset_balances for this snapshot (in case of update)
                    await conn.execute("DELETE FROM asset_balances WHERE snapshot_id = $1", snapshot_id)

                    # Bulk insert asset balances
                    assets = portfolio_data['balances']['assets']
                    if assets:
                        insert_assets = """
                        INSERT INTO asset_balances (
                            snapshot_id, asset_name, asset_fa_name, free_amount,
                            total_amount, usd_value, irr_value, has_balance,
                            is_fiat, is_digital_gold
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
                        )
                        """
                        # Use executemany for speed
                        records = []
                        for asset in assets:
                            records.append(
                                (
                                    snapshot_id,
                                    asset.get('asset'),
                                    asset.get('fa_name'),
                                    float(asset.get('free', 0) or 0),
                                    float(asset.get('total', 0) or 0),
                                    float(asset.get('usd_value', 0) or 0),
                                    float(asset.get('irr_value', 0) or 0),
                                    bool(asset.get('has_balance', False)),
                                    bool(asset.get('is_fiat', False)),
                                    bool(asset.get('is_digital_gold', False)),
                                )
                            )
                        await conn.executemany(insert_assets, records)

            logger.info(f"Portfolio snapshot saved successfully for {today}")
            return True
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
            return False

    async def get_portfolio_history(self, days: int = 30) -> List[Dict]:
        """Get portfolio history for the last N days"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, date, timestamp, total_usd_value, total_irr_value,
                           total_assets, assets_with_balance, account_email
                    FROM portfolio_snapshots
                    ORDER BY date DESC
                    LIMIT $1
                    """,
                    int(days),
                )
                history = [
                    {
                        'id': int(r['id']),
                        'date': r['date'].isoformat() if hasattr(r['date'], 'isoformat') else r['date'],
                        'timestamp': r['timestamp'].isoformat() if hasattr(r['timestamp'], 'isoformat') else r['timestamp'],
                        'total_usd_value': float(r['total_usd_value'] or 0),
                        'total_irr_value': float(r['total_irr_value'] or 0),
                        'total_assets': int(r['total_assets'] or 0),
                        'assets_with_balance': int(r['assets_with_balance'] or 0),
                        'account_email': r['account_email'],
                    }
                    for r in rows
                ]
                return history
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return []

    async def get_asset_history(self, asset_name: str, days: int = 30) -> List[Dict]:
        """Get balance history for a specific asset"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT ps.date, ab.free_amount, ab.total_amount,
                           ab.usd_value, ab.irr_value
                    FROM asset_balances ab
                    JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                    WHERE ab.asset_name = $1
                    ORDER BY ps.date DESC
                    LIMIT $2
                    """,
                    asset_name,
                    int(days),
                )
                history = [
                    {
                        'date': r['date'].isoformat() if hasattr(r['date'], 'isoformat') else r['date'],
                        'free_amount': float(r['free_amount'] or 0),
                        'total_amount': float(r['total_amount'] or 0),
                        'usd_value': float(r['usd_value'] or 0),
                        'irr_value': float(r['irr_value'] or 0),
                    }
                    for r in rows
                ]
                return history
        except Exception as e:
            logger.error(f"Error getting asset history for {asset_name}: {e}")
            return []

    async def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent portfolio snapshot"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT date, timestamp, total_usd_value, total_irr_value, 
                           total_assets, assets_with_balance, account_email, raw_data
                    FROM portfolio_snapshots
                    ORDER BY date DESC
                    LIMIT 1
                    """
                )
                if row:
                    return {
                        'date': row['date'].isoformat() if hasattr(row['date'], 'isoformat') else row['date'],
                        'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else row['timestamp'],
                        'total_usd_value': float(row['total_usd_value'] or 0),
                        'total_irr_value': float(row['total_irr_value'] or 0),
                        'total_assets': int(row['total_assets'] or 0),
                        'assets_with_balance': int(row['assets_with_balance'] or 0),
                        'account_email': row['account_email'],
                        'raw_data': row['raw_data']
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting latest snapshot: {e}")
            return None

    async def get_asset_balances_for_snapshot(self, snapshot_date: str) -> List[Dict]:
        """Get asset balances for a specific snapshot date"""
        try:
            # Convert string date to date object if needed
            if isinstance(snapshot_date, str):
                from datetime import datetime
                snapshot_date = datetime.strptime(snapshot_date, '%Y-%m-%d').date()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT ab.id, ab.asset_name, ab.asset_fa_name, ab.free_amount, 
                           ab.total_amount, ab.usd_value, ab.irr_value,
                           ab.has_balance, ab.is_fiat, ab.is_digital_gold,
                           ps.date as snapshot_date
                    FROM asset_balances ab
                    JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                    WHERE ps.date = $1
                    ORDER BY ab.usd_value DESC
                    """,
                    snapshot_date
                )
                
                assets = []
                for row in rows:
                    # Calculate locked balance (total - free)
                    free_balance = float(row['free_amount'] or 0)
                    total_balance = float(row['total_amount'] or 0)
                    locked_balance = max(0, total_balance - free_balance)
                    
                    # Calculate USD and IRR prices based on balance and value
                    usd_value = float(row['usd_value'] or 0)
                    irr_value = float(row['irr_value'] or 0)
                    usd_price = usd_value / total_balance if total_balance > 0 else 0
                    irr_price = irr_value / total_balance if total_balance > 0 else 0
                    
                    assets.append({
                        'id': int(row['id']),
                        'symbol': row['asset_name'],
                        'asset_name': row['asset_fa_name'] or row['asset_name'],
                        'free_balance': free_balance,
                        'locked_balance': locked_balance,
                        'total_balance': total_balance,
                        'usd_price': usd_price,
                        'usd_value': usd_value,
                        'irr_price': irr_price,
                        'irr_value': irr_value,
                        'has_balance': bool(row['has_balance']),
                        'is_fiat': bool(row['is_fiat']),
                        'is_digital_gold': bool(row['is_digital_gold']),
                        'snapshot_date': row['snapshot_date'].isoformat() if hasattr(row['snapshot_date'], 'isoformat') else row['snapshot_date']
                    })
                
                return assets
        except Exception as e:
            logger.error(f"Error getting asset balances for snapshot {snapshot_date}: {e}")
            return []

    async def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        try:
            async with self.pool.acquire() as conn:
                total_snapshots = await conn.fetchval("SELECT COUNT(*) FROM portfolio_snapshots")
                first_latest = await conn.fetchrow("SELECT MIN(date) AS first, MAX(date) AS latest FROM portfolio_snapshots")
                latest_values = await conn.fetchrow(
                    """
                    SELECT total_usd_value, total_irr_value
                    FROM portfolio_snapshots
                    ORDER BY date DESC
                    LIMIT 1
                    """
                )

                days_tracked = 0
                first_date = first_latest['first'] if first_latest else None
                latest_date = first_latest['latest'] if first_latest else None
                if first_date and latest_date:
                    try:
                        days_tracked = (latest_date - first_date).days + 1
                    except Exception as e:
                        logger.warning(f"Error calculating days tracked: {e}")
                        days_tracked = 0

                return {
                    'total_snapshots': int(total_snapshots or 0),
                    'first_snapshot': first_date.isoformat() if first_date else None,
                    'latest_snapshot': latest_date.isoformat() if latest_date else None,
                    'latest_usd_value': float(latest_values['total_usd_value']) if latest_values else 0,
                    'latest_irr_value': float(latest_values['total_irr_value']) if latest_values else 0,
                    'days_tracked': days_tracked,
                }
        except Exception as e:
            logger.error(f"Error getting portfolio stats: {e}")
            return {}

    async def get_coin_profit_comparison(self, days: int = 30) -> List[Dict]:
        """Get profit/loss comparison for individual coins"""
        try:
            async with self.pool.acquire() as conn:
                # Assets that currently have balances from the latest snapshot
                assets = await conn.fetch(
                    """
                    SELECT ab.asset_name, ab.asset_fa_name
                    FROM asset_balances ab
                    JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                    WHERE ab.has_balance = TRUE
                      AND ab.is_fiat = FALSE
                      AND ab.usd_value > 0
                      AND ps.date = (SELECT MAX(date) FROM portfolio_snapshots)
                    ORDER BY ab.usd_value DESC
                    """
                )

                coin_data: List[Dict] = []
                for r in assets:
                    asset_name = r['asset_name']
                    asset_fa_name = r['asset_fa_name']

                    first_record = await conn.fetchrow(
                        """
                        SELECT ps.date AS d, ab.usd_value AS v, ab.total_amount AS amt
                        FROM asset_balances ab
                        JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                        WHERE ab.asset_name = $1
                          AND ab.has_balance = TRUE
                          AND ps.date >= CURRENT_DATE - $2::INT
                        ORDER BY ps.date ASC
                        LIMIT 1
                        """,
                        asset_name,
                        int(days),
                    )

                    latest_record = await conn.fetchrow(
                        """
                        SELECT ps.date AS d, ab.usd_value AS v, ab.total_amount AS amt
                        FROM asset_balances ab
                        JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                        WHERE ab.asset_name = $1
                          AND ab.has_balance = TRUE
                          AND ps.date >= CURRENT_DATE - $2::INT
                        ORDER BY ps.date DESC
                        LIMIT 1
                        """,
                        asset_name,
                        int(days),
                    )

                    if first_record and latest_record:
                        first_value = float(first_record['v'] or 0)
                        latest_value = float(latest_record['v'] or 0)
                        profit_loss = latest_value - first_value
                        profit_loss_percentage = (profit_loss / first_value * 100) if first_value > 0 else 0.0

                        coin_data.append(
                            {
                                'symbol': asset_name,
                                'asset_name': asset_name,
                                'asset_fa_name': asset_fa_name or asset_name,
                                'first_date': first_record['d'].isoformat() if first_record['d'] else None,
                                'latest_date': latest_record['d'].isoformat() if latest_record['d'] else None,
                                'initial_value_usd': first_value,
                                'current_value_usd': latest_value,
                                'first_value': first_value,
                                'latest_value': latest_value,
                                'profit_loss_usd': profit_loss,
                                'profit_loss': profit_loss,
                                'profit_loss_percentage': profit_loss_percentage,
                                'amount': float(latest_record['amt'] or 0),
                            }
                        )

                coin_data.sort(key=lambda x: x['profit_loss_percentage'], reverse=True)
                return coin_data
        except Exception as e:
            logger.error(f"Error getting coin profit comparison: {e}")
            return []

    async def update_portfolio_snapshot(self, snapshot_id: int, data: Dict) -> bool:
        """Update a portfolio snapshot record"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE portfolio_snapshots 
                    SET total_usd_value = $1, total_irr_value = $2, 
                        total_assets = $3, assets_with_balance = $4,
                        account_email = $5
                    WHERE id = $6
                    """,
                    float(data.get('total_usd_value', 0)),
                    float(data.get('total_irr_value', 0)),
                    int(data.get('total_assets', 0)),
                    int(data.get('assets_with_balance', 0)),
                    data.get('account_email'),
                    snapshot_id
                )
            logger.info(f"Portfolio snapshot {snapshot_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating portfolio snapshot {snapshot_id}: {e}")
            return False

    async def delete_portfolio_snapshot(self, snapshot_id: int) -> bool:
        """Delete a portfolio snapshot record (cascade deletes asset balances)"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM portfolio_snapshots WHERE id = $1",
                    snapshot_id
                )
                # Check if any rows were actually deleted
                if result == "DELETE 0":
                    logger.warning(f"Portfolio snapshot {snapshot_id} not found")
                    return False
            logger.info(f"Portfolio snapshot {snapshot_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting portfolio snapshot {snapshot_id}: {e}")
            return False

    async def update_asset_balance(self, asset_id: int, data: Dict) -> bool:
        """Update an asset balance record"""
        try:
            # Build dynamic UPDATE query based on provided fields
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in data.items():
                if field in ['asset_name', 'asset_fa_name']:
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(value)
                elif field in ['free_amount', 'total_amount', 'usd_value', 'irr_value']:
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(float(value))
                elif field in ['has_balance', 'is_fiat', 'is_digital_gold']:
                    set_clauses.append(f"{field} = ${param_count}")
                    values.append(bool(value))
                param_count += 1
            
            if not set_clauses:
                logger.warning(f"No valid fields to update for asset {asset_id}")
                return False
            
            query = f"UPDATE asset_balances SET {', '.join(set_clauses)} WHERE id = ${param_count}"
            values.append(asset_id)
            
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *values)
                # Check if any rows were actually updated
                if result == "UPDATE 0":
                    logger.warning(f"Asset balance {asset_id} not found")
                    return False
            logger.info(f"Asset balance {asset_id} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating asset balance {asset_id}: {e}")
            return False

    async def delete_asset_balance(self, asset_id: int) -> bool:
        """Delete an asset balance record"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM asset_balances WHERE id = $1",
                    asset_id
                )
                # Check if any rows were actually deleted
                if result == "DELETE 0":
                    logger.warning(f"Asset balance {asset_id} not found")
                    return False
            logger.info(f"Asset balance {asset_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting asset balance {asset_id}: {e}")
            return False

    async def health(self) -> Dict:
        """Return health status of the database connection and schema."""
        try:
            if self.pool is None:
                await self.init()
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SHOW server_version;")
                can_select = await conn.fetchval("SELECT 1;")
                tables_rows = await conn.fetch(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('portfolio_snapshots', 'asset_balances')
                    """
                )
                tables = [r[0] for r in tables_rows]
                return {
                    'ok': True,
                    'server_version': str(version),
                    'select_1': int(can_select) == 1 if can_select is not None else False,
                    'tables_present': tables,
                    'pool_open': self.pool is not None,
                }
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return {
                'ok': False,
                'error': str(e)
            }

    async def get_coin_profit_comparison(self, days: int = 30) -> List[Dict]:
        """Get profit/loss comparison for individual coins"""
        try:
            async with self.pool.acquire() as conn:
                # Assets that currently have balances from the latest snapshot
                assets = await conn.fetch(
                    """
                    SELECT ab.asset_name, ab.asset_fa_name
                    FROM asset_balances ab
                    JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                    WHERE ab.has_balance = TRUE
                      AND ab.is_fiat = FALSE
                      AND ab.usd_value > 0
                      AND ps.date = (SELECT MAX(date) FROM portfolio_snapshots)
                    ORDER BY ab.usd_value DESC
                    """
                )

                coin_data: List[Dict] = []
                for r in assets:
                    asset_name = r['asset_name']
                    asset_fa_name = r['asset_fa_name']

                    first_record = await conn.fetchrow(
                        """
                        SELECT ps.date AS d, ab.usd_value AS v, ab.total_amount AS amt
                        FROM asset_balances ab
                        JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                        WHERE ab.asset_name = $1
                          AND ab.has_balance = TRUE
                          AND ps.date >= CURRENT_DATE - $2::INT
                        ORDER BY ps.date ASC
                        LIMIT 1
                        """,
                        asset_name,
                        int(days),
                    )

                    latest_record = await conn.fetchrow(
                        """
                        SELECT ps.date AS d, ab.usd_value AS v, ab.total_amount AS amt
                        FROM asset_balances ab
                        JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                        WHERE ab.asset_name = $1
                          AND ab.has_balance = TRUE
                          AND ps.date >= CURRENT_DATE - $2::INT
                        ORDER BY ps.date DESC
                        LIMIT 1
                        """,
                        asset_name,
                        int(days),
                    )

                    if first_record and latest_record:
                        first_value = float(first_record['v'] or 0)
                        latest_value = float(latest_record['v'] or 0)
                        profit_loss = latest_value - first_value
                        profit_loss_percentage = (profit_loss / first_value * 100) if first_value > 0 else 0.0

                        coin_data.append(
                            {
                                'symbol': asset_name,
                                'asset_name': asset_name,
                                'asset_fa_name': asset_fa_name or asset_name,
                                'first_date': first_record['d'].isoformat() if first_record['d'] else None,
                                'latest_date': latest_record['d'].isoformat() if latest_record['d'] else None,
                                'initial_value_usd': first_value,
                                'current_value_usd': latest_value,
                                'first_value': first_value,
                                'latest_value': latest_value,
                                'profit_loss_usd': profit_loss,
                                'profit_loss': profit_loss,
                                'profit_loss_percentage': profit_loss_percentage,
                                'amount': float(latest_record['amt'] or 0),
                            }
                        )

                coin_data.sort(key=lambda x: x['profit_loss_percentage'], reverse=True)
                return coin_data
        except Exception as e:
            logger.error(f"Error getting coin profit comparison: {e}")
            return []