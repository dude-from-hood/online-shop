import psycopg
from fastapi import APIRouter, HTTPException

from app.core.config import settings


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/db", summary="Check PostgreSQL connection")
def database_health_check() -> dict[str, str]:
    try:
        with psycopg.connect(settings.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Database is unavailable") from error

    return {"status": "ok", "database": "postgresql"}
