from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, relationship

from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class CollectionRun(BaseModel):
    __tablename__ = "collection_run"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    osint_source_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH),
        db.ForeignKey("osint_source.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collector_job_id: Mapped[str] = db.Column(db.String(), nullable=False, index=True)
    collector_type: Mapped[str] = db.Column(db.String(), nullable=False)
    manual: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)
    collector_started_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)
    collector_finished_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)
    collector_status: Mapped[str] = db.Column(db.String(), nullable=True)
    news_items_count: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    stored_bytes: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    expected_post_collection_bots: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    pipeline_finished_at: Mapped[datetime] = db.Column(db.DateTime, nullable=True)

    bot_completions: Mapped[list["CollectionRunBotCompletion"]] = relationship(
        "CollectionRunBotCompletion",
        back_populates="collection_run",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        osint_source_id: str,
        collector_job_id: str,
        collector_type: str,
        manual: bool = False,
        collector_started_at: datetime | None = None,
        id: str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.osint_source_id = osint_source_id
        self.collector_job_id = collector_job_id
        self.collector_type = collector_type
        self.manual = manual
        self.collector_started_at = collector_started_at or self.utcnow()
        self.news_items_count = 0
        self.stored_bytes = 0
        self.expected_post_collection_bots = 0

    @classmethod
    def start_run(
        cls,
        *,
        osint_source_id: str,
        collector_job_id: str,
        collector_type: str,
        manual: bool = False,
    ) -> "CollectionRun":
        run = cls(
            osint_source_id=osint_source_id,
            collector_job_id=collector_job_id,
            collector_type=collector_type,
            manual=manual,
        )
        db.session.add(run)
        db.session.commit()
        return run

    @classmethod
    def get_by_collector_job_id(cls, collector_job_id: str) -> "CollectionRun | None":
        return cls.get_first(
            db.select(cls).where(cls.collector_job_id == collector_job_id).order_by(cls.collector_started_at.desc(), cls.id.desc())
        )

    @classmethod
    def increment_ingested_news_items(
        cls,
        run_id: str,
        *,
        news_items_count: int,
        stored_bytes: int,
    ) -> "CollectionRun | None":
        run = cls.get(run_id)
        if run is None or news_items_count <= 0:
            return run

        run.news_items_count += max(int(news_items_count), 0)
        run.stored_bytes += max(int(stored_bytes), 0)
        db.session.commit()
        return run

    @classmethod
    def finish_collector(
        cls,
        run_id: str,
        *,
        collector_status: str,
        expected_post_collection_bots: int | None = None,
        collector_finished_at: datetime | None = None,
    ) -> "CollectionRun | None":
        run = cls.get(run_id)
        if run is None:
            return None

        run.collector_status = collector_status
        run.collector_finished_at = collector_finished_at or cls.utcnow()
        if expected_post_collection_bots is not None:
            run.expected_post_collection_bots = max(int(expected_post_collection_bots), 0)
        run._refresh_pipeline_finished_at()
        db.session.commit()
        return run

    @classmethod
    def record_bot_completion(
        cls,
        run_id: str,
        *,
        bot_id: str,
        bot_type: str,
        status: str,
        finished_at: datetime | None = None,
    ) -> "CollectionRun | None":
        run = cls.get(run_id)
        if run is None:
            return None

        completion = CollectionRunBotCompletion.get_for_run_and_bot(run_id, bot_id)
        if completion is None:
            completion = CollectionRunBotCompletion(
                collection_run_id=run_id,
                bot_id=bot_id,
                bot_type=bot_type,
                status=status,
                finished_at=finished_at or cls.utcnow(),
            )
            db.session.add(completion)
        else:
            completion.bot_type = bot_type
            completion.status = status
            completion.finished_at = finished_at or cls.utcnow()

        db.session.flush()
        run._refresh_pipeline_finished_at()
        db.session.commit()
        return run

    def _refresh_pipeline_finished_at(self) -> None:
        completed_bot_count = len(self.bot_completions)
        if self.collector_finished_at is None:
            self.pipeline_finished_at = None
            return

        if self.expected_post_collection_bots <= 0:
            self.pipeline_finished_at = self.collector_finished_at
            return

        if completed_bot_count < self.expected_post_collection_bots:
            self.pipeline_finished_at = None
            return

        latest_bot_finished = max((completion.finished_at for completion in self.bot_completions if completion.finished_at), default=None)
        if latest_bot_finished is None or latest_bot_finished < self.collector_finished_at:
            self.pipeline_finished_at = self.collector_finished_at
            return
        self.pipeline_finished_at = latest_bot_finished

    @classmethod
    def get_summary(cls, *, source_id: str | None = None, now: datetime | None = None) -> dict[str, Any]:
        now = now or cls.utcnow()
        cutoff = now - timedelta(hours=24)

        query = db.select(cls).where(cls.collector_finished_at.is_not(None)).where(cls.collector_finished_at >= cutoff)
        if source_id:
            query = query.where(cls.osint_source_id == source_id)

        runs = list(db.session.execute(query.order_by(cls.collector_finished_at.asc(), cls.id.asc())).scalars().all())

        items_24h = sum(run.news_items_count for run in runs)
        stored_bytes_24h = sum(run.stored_bytes for run in runs)

        peak_hour_started_at = None
        peak_hour_items = 0
        peak_hour_stored_bytes = 0
        hourly_buckets: dict[datetime, dict[str, int]] = {}
        for run in runs:
            if run.collector_finished_at is None:
                continue
            bucket_start = run.collector_finished_at.replace(minute=0, second=0, microsecond=0)
            bucket = hourly_buckets.setdefault(bucket_start, {"items": 0, "stored_bytes": 0})
            bucket["items"] += run.news_items_count
            bucket["stored_bytes"] += run.stored_bytes

        for bucket_start in sorted(hourly_buckets):
            bucket = hourly_buckets[bucket_start]
            bucket_items = bucket["items"]
            bucket_stored_bytes = bucket["stored_bytes"]
            if (
                bucket_items > peak_hour_items
                or (bucket_items == peak_hour_items and bucket_stored_bytes > peak_hour_stored_bytes)
                or (
                    bucket_items == peak_hour_items
                    and bucket_stored_bytes == peak_hour_stored_bytes
                    and (peak_hour_started_at is None or bucket_start > peak_hour_started_at)
                )
            ):
                peak_hour_started_at = bucket_start
                peak_hour_items = bucket_items
                peak_hour_stored_bytes = bucket_stored_bytes

        latency_seconds = sorted(
            int((run.pipeline_finished_at - run.collector_started_at).total_seconds())
            for run in runs
            if run.pipeline_finished_at is not None and run.news_items_count > 0
        )

        latency_avg_seconds = None
        latency_p95_seconds = None
        latency_max_seconds = None
        if latency_seconds:
            latency_avg_seconds = sum(latency_seconds) / len(latency_seconds)
            latency_max_seconds = max(latency_seconds)
            percentile_index = max(math.ceil(len(latency_seconds) * 0.95) - 1, 0)
            latency_p95_seconds = latency_seconds[percentile_index]

        return {
            "items_24h": items_24h,
            "stored_kb_24h": round(stored_bytes_24h / 1024, 1),
            "peak_hour_started_at": peak_hour_started_at.isoformat() if peak_hour_started_at else None,
            "peak_hour_items": peak_hour_items,
            "peak_hour_stored_kb": round(peak_hour_stored_bytes / 1024, 1),
            "latency_avg_seconds": latency_avg_seconds,
            "latency_p95_seconds": latency_p95_seconds,
            "latency_max_seconds": latency_max_seconds,
            "latency_sample_runs": len(latency_seconds),
        }


class CollectionRunBotCompletion(BaseModel):
    __tablename__ = "collection_run_bot_completion"
    __table_args__ = (UniqueConstraint("collection_run_id", "bot_id", name="uq_collection_run_bot_completion_run_bot"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    collection_run_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH),
        db.ForeignKey("collection_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), nullable=False)
    bot_type: Mapped[str] = db.Column(db.String(), nullable=False)
    status: Mapped[str] = db.Column(db.String(), nullable=False)
    finished_at: Mapped[datetime] = db.Column(db.DateTime, nullable=False, default=BaseModel.utcnow)

    collection_run: Mapped["CollectionRun"] = relationship("CollectionRun", back_populates="bot_completions")

    def __init__(
        self,
        collection_run_id: str,
        bot_id: str,
        bot_type: str,
        status: str,
        finished_at: datetime | None = None,
        id: str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.collection_run_id = collection_run_id
        self.bot_id = bot_id
        self.bot_type = bot_type
        self.status = status
        self.finished_at = finished_at or self.utcnow()

    @classmethod
    def get_for_run_and_bot(cls, collection_run_id: str, bot_id: str) -> "CollectionRunBotCompletion | None":
        stmt = db.select(cls).where(cls.collection_run_id == collection_run_id).where(cls.bot_id == bot_id)
        return cls.get_first(stmt)
