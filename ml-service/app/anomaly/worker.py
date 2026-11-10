"""Kafka consumer loop. Runs in a background thread next to the API."""

from __future__ import annotations

import logging
import threading

import psycopg
from confluent_kafka import Consumer, KafkaError, Message, Producer
from pydantic import ValidationError

from app.anomaly.detector import AnomalyDetector
from app.anomaly.events import PricePointRecorded
from app.anomaly.repository import PostgresAnomalyRepository
from app.core.config import Settings

log = logging.getLogger(__name__)
POLL_SECONDS = 1.0


class AnomalyWorker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="anomaly-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        s = self._settings
        consumer = Consumer(
            {
                "bootstrap.servers": s.kafka_bootstrap,
                "group.id": s.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        dlq = Producer({"bootstrap.servers": s.kafka_bootstrap})
        consumer.subscribe([s.topic])
        with psycopg.connect(s.database_url) as conn:
            detector = AnomalyDetector(
                PostgresAnomalyRepository(conn), s.z_threshold, s.min_group_history, s.history_weeks
            )
            try:
                while not self._stop.is_set():
                    msg = consumer.poll(POLL_SECONDS)
                    if msg is None:
                        continue
                    if err := msg.error():
                        if err.code() != KafkaError._PARTITION_EOF:
                            log.error("kafka error: %s", err)
                        continue
                    self._process(detector, msg, dlq)
                    consumer.commit(message=msg, asynchronous=False)
            finally:
                consumer.close()
                dlq.flush(5)

    def _process(self, detector: AnomalyDetector, msg: Message, dlq: Producer) -> None:
        payload = msg.value()
        try:
            event = PricePointRecorded.model_validate_json(payload or b"")
            detector.handle(event)
        except (ValidationError, ValueError):
            # Unreadable or wrong-type message: park it, do not block the partition.
            log.warning("moving message at offset %s to the dead-letter topic", msg.offset())
            dlq.produce(f"{self._settings.topic}.ml.dlq", key=msg.key(), value=payload)
