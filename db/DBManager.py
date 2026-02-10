from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
import psycopg2


load_dotenv()


class DBManager(ABC):
    """Connection/transaction/error handling is centralized here.
    Subclasses implement only SQL logic in execute_query().
    """

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL is not set")
        self.connection = None
        self.cursor = None

    @abstractmethod
    def execute_query(self, *args, **kwargs):
        """Implement SQL processing in subclasses."""
        raise NotImplementedError

    def query(self, *args, **kwargs):
        try:
            self.connection = psycopg2.connect(self.db_url)
            with self.connection:
                with self.connection.cursor() as cursor:
                    self.cursor = cursor
                    return self.execute_query(*args, **kwargs)
        except Exception as e:
            # with connection: automatically rolls back on exception.
            print(f"Failed to execute DB transaction: {e}")
            raise
        finally:
            self.cursor = None
            if self.connection is not None:
                self.connection.close()
                self.connection = None
