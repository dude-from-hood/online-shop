import json
import logging
import time
from threading import Event

import psycopg
from kafka import KafkaProducer

from app.core.config import settings
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(self, stop_event: Event) -> None:
        self.stop_event = stop_event
        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda value: str(value).encode("utf-8"),
        )

    def run(self) -> None:
        logger.info("Outbox publisher started")
        while not self.stop_event.is_set():
            self.publish_pending_events()
            self.stop_event.wait(2)
        self.producer.close()
        logger.info("Outbox publisher stopped")

    def publish_pending_events(self) -> None:
        try:
            with psycopg.connect(settings.database_url) as connection:
                events = OutboxRepository(connection).get_pending_events()
                for event in events:
                    try:
                        self.producer.send(
                            settings.kafka_orders_topic,
                            key=event["aggregate_id"],
                            value={
                                "event_id": str(event["id"]),
                                "event_type": event["event_type"],
                                "aggregate_type": event["aggregate_type"],
                                "aggregate_id": event["aggregate_id"],
                                "payload": event["payload"],
                            },
                        ).get(timeout=10)
                        OutboxRepository(connection).mark_as_processed(event["id"])
                    except Exception as error:
                        logger.exception("Failed to publish outbox event %s", event["id"])
                        OutboxRepository(connection).mark_as_failed(event["id"], str(error))
        except Exception:
            logger.exception("Outbox polling failed")
