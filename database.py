"""
Database module for portfolio tracking
Handles SQLite database operations for storing daily portfolio snapshots
"""

import sqlite3
import json
from datetime import datetime, date
from typing import Dict, List, Optional
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortfolioDatabase:
    """Handles portfolio data storage and retrieval"""
    
    def __init__(self, db_path: str = "portfolio_data.db"):
        """Initialize database connection and create tables if needed"""
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Create database tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create portfolio_snapshots table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        timestamp DATETIME NOT NULL,
                        total_usd_value REAL NOT NULL,
                        total_irr_value REAL NOT NULL,
                        total_assets INTEGER NOT NULL,
                        assets_with_balance INTEGER NOT NULL,
                        account_email TEXT,
                        account_user_id TEXT,
                        raw_data TEXT NOT NULL,
                        UNIQUE(date)
                    )
                """)
                
                # Create asset_balances table for detailed asset tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS asset_balances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_id INTEGER NOT NULL,
                        asset_name TEXT NOT NULL,
                        asset_fa_name TEXT,
                        free_amount REAL NOT NULL,
                        total_amount REAL NOT NULL,
                        usd_value REAL NOT NULL,
                        irr_value REAL NOT NULL,
                        has_balance BOOLEAN NOT NULL,
                        is_fiat BOOLEAN DEFAULT FALSE,
                        is_digital_gold BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots (id)
                    )
                """)
                
                # Create index for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_portfolio_date 
                    ON portfolio_snapshots(date)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_asset_snapshot 
                    ON asset_balances(snapshot_id, asset_name)
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def save_portfolio_snapshot(self, portfolio_data: Dict) -> bool:
        """Save a daily portfolio snapshot to the database"""
        try:
            today = date.today()
            timestamp = datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if snapshot for today already exists
                cursor.execute(
                    "SELECT id FROM portfolio_snapshots WHERE date = ?",
                    (today,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"Portfolio snapshot for {today} already exists, updating...")
                    snapshot_id = existing[0]
                    
                    # Update existing snapshot
                    cursor.execute("""
                        UPDATE portfolio_snapshots 
                        SET timestamp = ?, total_usd_value = ?, total_irr_value = ?,
                            total_assets = ?, assets_with_balance = ?, 
                            account_email = ?, account_user_id = ?, raw_data = ?
                        WHERE id = ?
                    """, (
                        timestamp,
                        portfolio_data['balances']['total_usd_value'],
                        portfolio_data['balances']['total_irr_value'],
                        portfolio_data['balances']['total_assets'],
                        portfolio_data['balances']['assets_with_balance'],
                        portfolio_data['account']['email'],
                        portfolio_data['account']['user_id'],
                        json.dumps(portfolio_data),
                        snapshot_id
                    ))
                    
                    # Delete existing asset balances for this snapshot
                    cursor.execute("DELETE FROM asset_balances WHERE snapshot_id = ?", (snapshot_id,))
                    
                else:
                    # Insert new snapshot
                    cursor.execute("""
                        INSERT INTO portfolio_snapshots 
                        (date, timestamp, total_usd_value, total_irr_value, 
                         total_assets, assets_with_balance, account_email, 
                         account_user_id, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        today,
                        timestamp,
                        portfolio_data['balances']['total_usd_value'],
                        portfolio_data['balances']['total_irr_value'],
                        portfolio_data['balances']['total_assets'],
                        portfolio_data['balances']['assets_with_balance'],
                        portfolio_data['account']['email'],
                        portfolio_data['account']['user_id'],
                        json.dumps(portfolio_data)
                    ))
                    
                    snapshot_id = cursor.lastrowid
                
                # Insert asset balances
                for asset in portfolio_data['balances']['assets']:
                    cursor.execute("""
                        INSERT INTO asset_balances 
                        (snapshot_id, asset_name, asset_fa_name, free_amount, 
                         total_amount, usd_value, irr_value, has_balance, 
                         is_fiat, is_digital_gold)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        snapshot_id,
                        asset['asset'],
                        asset['fa_name'],
                        asset['free'],
                        asset['total'],
                        asset['usd_value'],
                        asset['irr_value'],
                        asset['has_balance'],
                        asset.get('is_fiat', False),
                        asset.get('is_digital_gold', False)
                    ))
                
                conn.commit()
                logger.info(f"Portfolio snapshot saved successfully for {today}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
            return False
    
    def get_portfolio_history(self, days: int = 30) -> List[Dict]:
        """Get portfolio history for the last N days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT date, timestamp, total_usd_value, total_irr_value,
                           total_assets, assets_with_balance, account_email
                    FROM portfolio_snapshots 
                    ORDER BY date DESC 
                    LIMIT ?
                """, (days,))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        'date': row[0],
                        'timestamp': row[1],
                        'total_usd_value': row[2],
                        'total_irr_value': row[3],
                        'total_assets': row[4],
                        'assets_with_balance': row[5],
                        'account_email': row[6]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return []
    
    def get_asset_history(self, asset_name: str, days: int = 30) -> List[Dict]:
        """Get balance history for a specific asset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT ps.date, ab.free_amount, ab.total_amount, 
                           ab.usd_value, ab.irr_value
                    FROM asset_balances ab
                    JOIN portfolio_snapshots ps ON ab.snapshot_id = ps.id
                    WHERE ab.asset_name = ?
                    ORDER BY ps.date DESC
                    LIMIT ?
                """, (asset_name, days))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    history.append({
                        'date': row[0],
                        'free_amount': row[1],
                        'total_amount': row[2],
                        'usd_value': row[3],
                        'irr_value': row[4]
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"Error getting asset history for {asset_name}: {e}")
            return []
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent portfolio snapshot"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT raw_data FROM portfolio_snapshots 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest snapshot: {e}")
            return None
    
    def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total snapshots
                cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
                total_snapshots = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute("""
                    SELECT MIN(date), MAX(date) FROM portfolio_snapshots
                """)
                date_range = cursor.fetchone()
                
                # Get latest values
                cursor.execute("""
                    SELECT total_usd_value, total_irr_value 
                    FROM portfolio_snapshots 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                latest_values = cursor.fetchone()
                
                # Calculate days tracked
                days_tracked = 0
                if date_range[0] and date_range[1]:
                    try:
                        from datetime import datetime
                        first_date = datetime.strptime(date_range[0], '%Y-%m-%d').date()
                        latest_date = datetime.strptime(date_range[1], '%Y-%m-%d').date()
                        days_tracked = (latest_date - first_date).days + 1
                    except Exception as e:
                        logger.warning(f"Error calculating days tracked: {e}")
                        days_tracked = 0
                
                return {
                    'total_snapshots': total_snapshots,
                    'first_snapshot': date_range[0],
                    'latest_snapshot': date_range[1],
                    'latest_usd_value': latest_values[0] if latest_values else 0,
                    'latest_irr_value': latest_values[1] if latest_values else 0,
                    'days_tracked': days_tracked
                }
                
        except Exception as e:
            logger.error(f"Error getting portfolio stats: {e}")
            return {}