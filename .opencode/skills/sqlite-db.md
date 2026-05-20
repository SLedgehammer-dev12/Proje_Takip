# SQLite Optimization Skill

Bu skill, projede kullanılan SQLite optimizasyon desenlerini tanımlar.

## Connection Management
- WAL mode: `PRAGMA journal_mode=WAL`
- Busy timeout: 10s (local), 30s (network)
- Cache: 64MB (local), 128MB (network)
- Synchronous: NORMAL (local), FULL (network)

## Migration Pattern
```python
def _ensure_migration(self):
    try:
        columns = self._get_table_columns("revizyonlar")
        pending = []
        if "new_column" not in columns:
            pending.append("ALTER TABLE revizyonlar ADD COLUMN new_column TEXT")
        if not pending:
            return
        with self.transaction(track_change=False):
            for sql in pending:
                self.cursor.execute(sql)
    except Exception:
        pass  # Idempotent: column already exists
```

## Query Pattern
- Tüm kullanıcı girdileri parametrize: `cursor.execute("SELECT * FROM t WHERE x = ?", (val,))`
- Filtreleme: `_build_sql_condition()` ile `EXISTS`/`NOT EXISTS` subquery
- Read connection pool: `acquire_read_connection()` / `release_read_connection()` (henüz aktif değil)

## Cache Pattern
- Query cache: `_query_cache` dict with TTL (30s)
- Filter cache: hash-based, capped at 1000 results
- PDF render cache: `OrderedDict` with LRU eviction (5MB limit)

## Performance Mode
- PDF zoom: max 1.35x (vs 2.0x normal)
- Max dimension: 2200px (vs 3500px normal)
- PDF cache: 2MB limit (vs 5MB normal)
- UI cache: 200 max (vs 500 normal)
