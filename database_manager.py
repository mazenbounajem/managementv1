import pyodbc
import logging
import asyncio
from contextlib import contextmanager
from queue import Queue, Empty
from threading import Lock
import time

# Enable pyodbc's built-in connection pooling at the driver level
pyodbc.pooling = True


class DatabaseManager:
    """Centralized database connection manager with connection pooling.

    Changes from the original single-connection-per-query approach:
    • pyodbc.pooling is enabled globally (ODBC driver-level pooling)
    • An application-level pool (Queue) reuses connections across queries
    • Stale connections are detected and discarded automatically
    • Async wrappers allow non-blocking DB calls from the NiceGUI event loop
    """

    # Configuration - change these values to switch databases
    CONNECTION_CONFIG = {
        "driver": "SQL Server Native Client 11.0",
        "server": "DESKTOP-Q7U1STD\\SQLEXPRESS02",
        "database": "POSDB",
        "trusted_connection": "yes"
    }

    # Pool settings
    POOL_SIZE = 5          # max idle connections kept in the pool
    POOL_TIMEOUT = 30      # seconds to wait for a connection
    MAX_CONN_AGE = 300     # seconds before a connection is considered stale

    def __init__(self):
        self.connection_string = self._build_connection_string()
        self._pool = Queue(maxsize=self.POOL_SIZE)
        self._lock = Lock()
        self._created_count = 0

    def _build_connection_string(self):
        """Build connection string from configuration"""
        return (
            f"Driver={{{self.CONNECTION_CONFIG['driver']}}};"
            f"Server={self.CONNECTION_CONFIG['server']};"
            f"Database={self.CONNECTION_CONFIG['database']};"
            f"Trusted_Connection={self.CONNECTION_CONFIG['trusted_connection']};"
        )

    def _create_connection(self):
        """Create a new database connection"""
        conn = pyodbc.connect(self.connection_string)
        with self._lock:
            self._created_count += 1
        return conn, time.time()

    def _is_connection_valid(self, conn, created_at):
        """Check if a pooled connection is still usable"""
        try:
            # Check age
            if time.time() - created_at > self.MAX_CONN_AGE:
                return False
            # Quick ping
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False

    def _get_from_pool(self):
        """Get a connection from the pool, or create a new one"""
        # Try to reuse an existing pooled connection
        while True:
            try:
                conn_tuple = self._pool.get_nowait()
                # Handle possible old queue items before the update if any
                if isinstance(conn_tuple, tuple) and len(conn_tuple) == 2:
                    conn, created_at = conn_tuple
                else:
                    conn = conn_tuple
                    created_at = time.time()

                if self._is_connection_valid(conn, created_at):
                    return conn, created_at
                else:
                    # Discard stale connection
                    try:
                        conn.close()
                    except Exception:
                        pass
            except Empty:
                break

        # No pooled connection available — create a fresh one
        return self._create_connection()

    def _return_to_pool(self, conn, created_at):
        """Return a connection back to the pool for reuse"""
        try:
            if self._is_connection_valid(conn, created_at):
                try:
                    self._pool.put_nowait((conn, created_at))
                    return
                except Exception:
                    pass
            # Pool is full or connection is stale — close it
            conn.close()
        except Exception:
            pass

    @contextmanager
    def get_connection(self):
        """Context manager for database connections (pooled)"""
        conn = None
        created_at = None
        try:
            conn, created_at = self._get_from_pool()
            yield conn
        except Exception as e:
            # On error, discard the connection instead of returning it
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                conn = None
            logging.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if conn and created_at is not None:
                self._return_to_pool(conn, created_at)

    def execute_query(self, sql, params=None):
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchall()

    def execute_update(self, sql, params=None):
        """Execute INSERT/UPDATE/DELETE queries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor.rowcount

    def execute_scalar(self, sql, params=None):
        """Execute query and return single value"""
        results = self.execute_query(sql, params)
        return results[0][0] if results else None

    # ── Async wrappers (Phase 6) ─────────────────────────────────────

    async def execute_query_async(self, sql, params=None):
        """Non-blocking SELECT — runs in a thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_query, sql, params)

    async def execute_update_async(self, sql, params=None):
        """Non-blocking INSERT/UPDATE/DELETE — runs in a thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_update, sql, params)

    async def execute_scalar_async(self, sql, params=None):
        """Non-blocking scalar query — runs in a thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute_scalar, sql, params)

    # ── Diagnostics ──────────────────────────────────────────────────

    @property
    def pool_status(self):
        """Return pool stats for monitoring"""
        return {
            'idle': self._pool.qsize(),
            'max_idle': self.POOL_SIZE,
            'total_created': self._created_count,
        }


# Create global instance
db_manager = DatabaseManager()
