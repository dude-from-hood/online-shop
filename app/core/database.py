from collections.abc import Generator

import psycopg

from app.core.config import settings


def get_connection() -> Generator[psycopg.Connection, None, None]:
    connection = psycopg.connect(settings.database_url)
    try:
        yield connection
    finally:
        connection.close()
