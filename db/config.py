import os
from urllib.parse import urlencode, quote


DEFAULT_DATABASE_URL = "postgresql://hate2action:hate2action@localhost:5433/hate2action"


def get_database_url(default: str = DEFAULT_DATABASE_URL) -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")

    if not db_name or not db_user:
        return default

    password_part = f":{quote(db_password, safe='')}" if db_password else ""
    user_part = quote(db_user, safe="")
    db_name_part = quote(db_name, safe="")

    if db_host:
        return _build_database_url(
            user_part=user_part,
            password_part=password_part,
            db_name_part=db_name_part,
            host=db_host,
            port=db_port,
        )

    if instance_connection_name:
        return _build_database_url(
            user_part=user_part,
            password_part=password_part,
            db_name_part=db_name_part,
            host=f"/cloudsql/{instance_connection_name}",
            port=db_port,
        )

    return default


def _build_database_url(
    *,
    user_part: str,
    password_part: str,
    db_name_part: str,
    host: str,
    port: str | None,
) -> str:
    if host.startswith("/"):
        query = {"host": host}
        if port:
            query["port"] = port
        return (
            f"postgresql://{user_part}{password_part}@/{db_name_part}"
            f"?{urlencode(query)}"
        )

    port_part = f":{port}" if port else ""
    return f"postgresql://{user_part}{password_part}@{host}{port_part}/{db_name_part}"
