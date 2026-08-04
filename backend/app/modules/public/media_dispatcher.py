from uuid import UUID


class CeleryPublicMediaDispatcher:
    def enqueue(self, relation_id: UUID) -> None:
        from app.workers.public_media_tasks import generate_public_media_derivative

        generate_public_media_derivative.delay(str(relation_id))
