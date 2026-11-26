"""Owner-only moving timeline, KES budget, and room setup planning."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.services import (
    MoveBudgetItem,
    MovePlan,
    MovePlanTask,
    RoomSetupItem,
    ServiceBooking,
)
from app.schemas.services import (
    MoveBudgetCreate,
    MoveBudgetResponse,
    MovePlanCreate,
    MovePlanResponse,
    MoveTaskCreate,
    MoveTaskResponse,
    MoveTaskStatus,
    RoomSetupCreate,
    RoomSetupResponse,
    RoomSetupStatus,
)
from app.services.authorization import AuthorizationService
from app.services.service_catalog import ServiceCatalogService


class MovingPlanService:
    def __init__(self) -> None:
        self.authorization = AuthorizationService()
        self.catalog = ServiceCatalogService()

    def create_plan(
        self, session: Session, *, user_id: UUID, body: MovePlanCreate
    ) -> MovePlanResponse:
        self._permission(session, user_id)
        row = MovePlan(
            owner_user_id=user_id,
            title=body.title,
            move_date=body.move_date,
            target_budget_kes=body.target_budget_kes,
        )
        session.add(row)
        session.commit()
        return MovePlanResponse.model_validate(row)

    def plans(self, session: Session, *, user_id: UUID) -> list[MovePlanResponse]:
        self._permission(session, user_id)
        rows = session.scalars(
            select(MovePlan)
            .where(MovePlan.owner_user_id == user_id)
            .order_by(MovePlan.move_date.is_(None), MovePlan.move_date, MovePlan.created_at.desc())
        )
        return [MovePlanResponse.model_validate(row) for row in rows]

    def update_plan(
        self, session: Session, *, user_id: UUID, plan_id: UUID, body: MovePlanCreate
    ) -> MovePlanResponse:
        row = self._plan(session, user_id, plan_id)
        row.title = body.title
        row.move_date = body.move_date
        row.target_budget_kes = body.target_budget_kes
        row.updated_at = datetime.now(UTC)
        session.commit()
        return MovePlanResponse.model_validate(row)

    def delete_plan(self, session: Session, *, user_id: UUID, plan_id: UUID) -> None:
        row = self._plan(session, user_id, plan_id)
        session.delete(row)
        session.commit()

    def tasks(self, session: Session, *, user_id: UUID, plan_id: UUID) -> list[MoveTaskResponse]:
        self._plan(session, user_id, plan_id)
        rows = session.scalars(
            select(MovePlanTask)
            .where(MovePlanTask.move_plan_id == plan_id)
            .order_by(
                MovePlanTask.due_date.is_(None), MovePlanTask.due_date, MovePlanTask.created_at
            )
        )
        return [MoveTaskResponse.model_validate(row) for row in rows]

    def calendar(
        self, session: Session, *, user_id: UUID, start_date, end_date
    ) -> list[MoveTaskResponse]:
        self._permission(session, user_id)
        if end_date < start_date:
            raise ApiError(
                422, "invalid_calendar_range", "End date must be on or after the start date."
            )
        rows = session.scalars(
            select(MovePlanTask)
            .join(MovePlan, MovePlan.id == MovePlanTask.move_plan_id)
            .where(
                MovePlan.owner_user_id == user_id,
                MovePlanTask.due_date >= start_date,
                MovePlanTask.due_date <= end_date,
            )
            .order_by(MovePlanTask.due_date, MovePlanTask.created_at)
        )
        return [MoveTaskResponse.model_validate(row) for row in rows]

    def create_task(
        self, session: Session, *, user_id: UUID, plan_id: UUID, body: MoveTaskCreate
    ) -> MoveTaskResponse:
        self._plan(session, user_id, plan_id)
        if body.provider_offering_id:
            self.catalog.public_offering(session, service_id=body.provider_offering_id)
        if body.booking_id:
            booking = session.get(ServiceBooking, body.booking_id)
            if booking is None or booking.customer_user_id != user_id:
                raise self._not_found()
            if body.provider_offering_id and body.provider_offering_id != booking.offering_id:
                raise ApiError(
                    422, "booking_service_mismatch", "Choose the service linked to this booking."
                )
        row = MovePlanTask(
            move_plan_id=plan_id,
            title=body.title.strip(),
            details=body.details.strip() if body.details else None,
            category=body.category,
            due_date=body.due_date,
            provider_offering_id=body.provider_offering_id,
            booking_id=body.booking_id,
            status="open",
        )
        session.add(row)
        session.commit()
        return MoveTaskResponse.model_validate(row)

    def update_task(
        self, session: Session, *, user_id: UUID, task_id: UUID, body: MoveTaskStatus
    ) -> MoveTaskResponse:
        row = self._task(session, user_id, task_id)
        row.status = body.status
        row.completed_at = datetime.now(UTC) if body.status == "completed" else None
        row.updated_at = datetime.now(UTC)
        session.commit()
        return MoveTaskResponse.model_validate(row)

    def budget_items(
        self, session: Session, *, user_id: UUID, plan_id: UUID
    ) -> list[MoveBudgetResponse]:
        self._plan(session, user_id, plan_id)
        rows = session.scalars(
            select(MoveBudgetItem)
            .where(MoveBudgetItem.move_plan_id == plan_id, MoveBudgetItem.owner_user_id == user_id)
            .order_by(MoveBudgetItem.created_at.desc())
        )
        return [MoveBudgetResponse.model_validate(row) for row in rows]

    def add_budget_item(
        self, session: Session, *, user_id: UUID, plan_id: UUID, body: MoveBudgetCreate
    ) -> MoveBudgetResponse:
        self._plan(session, user_id, plan_id)
        if body.provider_offering_id:
            self.catalog.public_offering(session, service_id=body.provider_offering_id)
        row = MoveBudgetItem(
            move_plan_id=plan_id,
            owner_user_id=user_id,
            title=body.title.strip(),
            amount_kes=body.amount_kes,
            provider_offering_id=body.provider_offering_id,
        )
        session.add(row)
        session.commit()
        return MoveBudgetResponse.model_validate(row)

    def room_items(
        self, session: Session, *, user_id: UUID, plan_id: UUID
    ) -> list[RoomSetupResponse]:
        self._plan(session, user_id, plan_id)
        rows = session.scalars(
            select(RoomSetupItem)
            .where(RoomSetupItem.move_plan_id == plan_id, RoomSetupItem.owner_user_id == user_id)
            .order_by(RoomSetupItem.room_name, RoomSetupItem.created_at)
        )
        return [RoomSetupResponse.model_validate(row) for row in rows]

    def add_room_item(
        self, session: Session, *, user_id: UUID, plan_id: UUID, body: RoomSetupCreate
    ) -> RoomSetupResponse:
        self._plan(session, user_id, plan_id)
        row = RoomSetupItem(
            move_plan_id=plan_id,
            owner_user_id=user_id,
            room_name=body.room_name.strip(),
            item_name=body.item_name.strip(),
            quantity=body.quantity,
            estimated_cost_kes=body.estimated_cost_kes,
        )
        session.add(row)
        session.commit()
        return RoomSetupResponse.model_validate(row)

    def update_room_item(
        self, session: Session, *, user_id: UUID, item_id: UUID, body: RoomSetupStatus
    ) -> RoomSetupResponse:
        row = session.get(RoomSetupItem, item_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        row.status = body.status
        row.updated_at = datetime.now(UTC)
        session.commit()
        return RoomSetupResponse.model_validate(row)

    def _task(self, session: Session, user_id: UUID, task_id: UUID) -> MovePlanTask:
        row = session.get(MovePlanTask, task_id)
        if row is None:
            raise self._not_found()
        self._plan(session, user_id, row.move_plan_id)
        return row

    def _plan(self, session: Session, user_id: UUID, plan_id: UUID) -> MovePlan:
        self._permission(session, user_id)
        row = session.get(MovePlan, plan_id)
        if row is None or row.owner_user_id != user_id:
            raise self._not_found()
        return row

    def _permission(self, session: Session, user_id: UUID) -> None:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="move_plan:manage:self",
            resource_owner_id=user_id,
        )

    @staticmethod
    def _not_found() -> ApiError:
        return ApiError(404, "move_plan_not_found", "The requested moving plan item was not found.")
