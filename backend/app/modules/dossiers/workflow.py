from collections.abc import Collection
from uuid import UUID

from app.modules.dossiers.errors import DossierInvalidStateError
from app.modules.dossiers.models import (
    Dossier,
    DossierStatus,
    DossierStatusHistory,
)
from app.modules.dossiers.repository import DossierRepository


class DossierWorkflowService:
    def __init__(self, repository: DossierRepository) -> None:
        self._repository = repository

    def transition(
        self,
        dossier: Dossier,
        *,
        target: DossierStatus,
        actor_user_id: UUID,
        allowed_sources: Collection[DossierStatus],
        reason_code: str,
        note: str | None = None,
    ) -> DossierStatusHistory:
        source = dossier.status
        if source not in allowed_sources:
            raise DossierInvalidStateError(
                f"Transition from {source.value} to {target.value} is not allowed."
            )
        history = DossierStatusHistory(
            dossier_id=dossier.id,
            from_status=source,
            to_status=target,
            actor_user_id=actor_user_id,
            reason_code=reason_code,
            note=note,
        )
        self._repository.add_status_history(history)
        dossier._set_status_from_workflow(target)
        return history
