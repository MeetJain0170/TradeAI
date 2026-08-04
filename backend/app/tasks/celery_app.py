"""Celery application instance and configuration."""

from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]
from config.settings import get_settings

settings = get_settings()

celery_app = Celery(
    "tradeai_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "ingest-market-data-every-60s": {
            "task": "app.tasks.market_data_ingestion.ingest_latest_market_data",
            "schedule": 60.0,
        },
    },
)
