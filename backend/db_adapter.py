import os
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

class DatabaseClient:
    """
    Adapter layer to ensure stable, predictable database row shapes.
    Enforces Rule 1 (Explicit row shape) and Rule 2 (Normalization at boundary).
    """

    def __init__(self, sqlalchemy_url: str):
        self.url = sqlalchemy_url
        self.engine = create_engine(self.url)

    def fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a query and returns all rows as a list of dictionaries.
        Enforces Rule 4 (Structural assertions).
        """
        if params is None:
            params = {}

        with self.engine.connect() as conn:
            result = conn.execute(text(query), params)
            if not result.returns_rows:
                return []
            
            # Rule 2: Normalize at the boundary
            # SQLAlchemy Result objects can be converted to dicts using .mappings()
            rows = [dict(row) for row in result.mappings()]

        # Rule 4: Structural assertions
        assert isinstance(rows, list), f"Expected list, got {type(rows)}"
        if rows:
            assert isinstance(rows[0], dict), f"Expected dict rows, got {type(rows[0])}"
        
        return rows

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None, commit: bool = True) -> int:
        """
        Executes a non-selection query (INSERT, UPDATE, DELETE) and returns rowcount.
        """
        if params is None:
            params = {}

        with self.engine.connect() as conn:
            if commit:
                with conn.begin():
                    result = conn.execute(text(query), params)
                    rowcount = result.rowcount
            else:
                result = conn.execute(text(query), params)
                rowcount = result.rowcount
            return rowcount

    def get_inspector(self):
        return inspect(self.engine)

    def dispose(self):
        self.engine.dispose()
