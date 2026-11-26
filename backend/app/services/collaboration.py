"""Shared search groups, opt-in roommate discovery, and private comparisons."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.location import County, Town
from app.models.notification import InAppNotification
from app.models.phase10 import (
    CollaborationGroup,
    CollaborationGroupMember,
    ComparisonBoard,
    ComparisonItem,
    Conversation,
    ConversationParticipant,
    RoommateInterest,
    RoommateProfile,
    SharedComparison,
    SharedMoveGoal,
    SharedMoveGoalConsent,
    SharedProperty,
    SharedPropertyComment,
    SharedPropertyVote,
    SharedSearch,
    SharedTask,
)
from app.models.property import Property, PropertyAmenity
from app.models.user import UserAccount
from app.schemas.phase10 import (
    ComparisonBoardResponse,
    ComparisonBoardSave,
    GroupCreate,
    GroupInvite,
    GroupMemberResponse,
    GroupResponse,
    RoommateCandidateResponse,
    RoommateInterestDecision,
    RoommateInterestResponse,
    RoommateProfileResponse,
    RoommateProfileSave,
    SharedComparisonSave,
    SharedFinancialConsent,
    SharedMoveGoalCreate,
    SharedPropertyAdd,
    SharedPropertyCommentCreate,
    SharedPropertyVoteInput,
    SharedSearchCreate,
    SharedTaskCreate,
    SharedTaskUpdate,
)
from app.services.authorization import AuthorizationService
from app.services.phase10_cipher import Phase10Cipher


class CollaborationService:
    def __init__(self, cipher: Phase10Cipher) -> None:
        self.cipher = cipher
        self.authorization = AuthorizationService()

    def create_group(self, session: Session, user_id: UUID, body: GroupCreate) -> GroupResponse:
        self._permission(
            session, user_id, "shared_group:create:self", scope="user", scope_id=str(user_id)
        )
        group = CollaborationGroup(name=body.name, created_by_user_id=user_id)
        session.add(group)
        session.flush()
        session.add(
            CollaborationGroupMember(
                group_id=group.id,
                user_id=user_id,
                invited_by_user_id=user_id,
                role="owner",
                status="active",
                responded_at=datetime.now(UTC),
            )
        )
        conversation = Conversation(group_id=group.id, created_by_user_id=user_id)
        session.add(conversation)
        session.flush()
        session.add(ConversationParticipant(conversation_id=conversation.id, user_id=user_id))
        session.flush()
        for invite_id in body.invite_user_ids:
            if invite_id == user_id:
                raise ApiError(422, "cannot_invite_self", "You are already the group owner.")
            self._invite_account(session, group, user_id, invite_id)
        session.commit()
        return self._group_response(session, group, user_id)

    def groups(self, session: Session, user_id: UUID) -> list[GroupResponse]:
        memberships = list(
            session.scalars(
                select(CollaborationGroupMember)
                .where(
                    CollaborationGroupMember.user_id == user_id,
                    CollaborationGroupMember.status.in_(("active", "invited")),
                )
                .order_by(CollaborationGroupMember.created_at.desc())
            )
        )
        return [
            self._group_response(session, session.get(CollaborationGroup, item.group_id), user_id)
            for item in memberships
            if session.get(CollaborationGroup, item.group_id) is not None
        ]

    def invite(
        self, session: Session, user_id: UUID, group_id: UUID, body: GroupInvite
    ) -> GroupResponse:
        group = self._require_group_owner(session, group_id, user_id)
        self._invite_account(session, group, user_id, body.user_id)
        session.commit()
        return self._group_response(session, group, user_id)

    def respond_to_invitation(
        self, session: Session, user_id: UUID, group_id: UUID, *, accept: bool
    ) -> GroupResponse:
        membership = session.get(CollaborationGroupMember, (group_id, user_id))
        group = session.get(CollaborationGroup, group_id)
        if membership is None or group is None or membership.status != "invited":
            raise self.not_found("The invitation was not found.")
        membership.status = "active" if accept else "declined"
        membership.responded_at = datetime.now(UTC)
        if accept:
            conversation = session.scalar(
                select(Conversation).where(Conversation.group_id == group.id)
            )
            if conversation is not None:
                participant = session.get(ConversationParticipant, (conversation.id, user_id))
                if participant is None:
                    session.add(
                        ConversationParticipant(conversation_id=conversation.id, user_id=user_id)
                    )
                else:
                    participant.is_active = True
                    participant.archived_at = None
            session.add(
                InAppNotification(
                    recipient_user_id=group.created_by_user_id,
                    category="shared_group",
                    title="Group invitation accepted",
                    body="A HomeScout member joined your shared search group.",
                    target_path="/collaboration?tab=Groups",
                )
            )
        session.commit()
        return self._group_response(session, group, user_id)

    def revoke_member(
        self, session: Session, user_id: UUID, group_id: UUID, target_user_id: UUID
    ) -> None:
        group = self._require_group_owner(session, group_id, user_id)
        if target_user_id == group.created_by_user_id:
            raise ApiError(409, "cannot_revoke_group_owner", "The group owner cannot be removed.")
        membership = session.get(CollaborationGroupMember, (group_id, target_user_id))
        if membership is None or membership.status not in {"active", "invited"}:
            raise self.not_found("The group member was not found.")
        membership.status = "revoked"
        membership.responded_at = datetime.now(UTC)
        conversation = session.scalar(select(Conversation).where(Conversation.group_id == group_id))
        if conversation:
            participant = session.get(ConversationParticipant, (conversation.id, target_user_id))
            if participant:
                participant.is_active = False
        session.commit()

    def create_shared_search(
        self, session: Session, user_id: UUID, group_id: UUID, body: SharedSearchCreate
    ) -> SharedSearch:
        self._require_group_member(session, group_id, user_id)
        row = SharedSearch(
            group_id=group_id,
            created_by_user_id=user_id,
            name=body.name,
            filters=body.filters,
        )
        session.add(row)
        session.commit()
        return row

    def shared_searches(
        self, session: Session, user_id: UUID, group_id: UUID
    ) -> list[SharedSearch]:
        self._require_group_member(session, group_id, user_id)
        return list(
            session.scalars(
                select(SharedSearch)
                .where(SharedSearch.group_id == group_id)
                .order_by(SharedSearch.updated_at.desc())
            )
        )

    def add_property(
        self, session: Session, user_id: UUID, group_id: UUID, body: SharedPropertyAdd
    ) -> SharedProperty:
        self._require_group_member(session, group_id, user_id)
        property_ = self._require_public_property(session, body.property_id)
        row = session.scalar(
            select(SharedProperty).where(
                SharedProperty.group_id == group_id,
                SharedProperty.property_id == property_.id,
            )
        )
        if row is None:
            row = SharedProperty(
                group_id=group_id,
                property_id=property_.id,
                added_by_user_id=user_id,
            )
            session.add(row)
            session.commit()
        return row

    def shared_properties(
        self, session: Session, user_id: UUID, group_id: UUID
    ) -> list[dict[str, object]]:
        self._require_group_member(session, group_id, user_id)
        rows = list(
            session.scalars(
                select(SharedProperty)
                .where(SharedProperty.group_id == group_id)
                .order_by(SharedProperty.created_at.desc())
            )
        )
        result = []
        for row in rows:
            property_ = self._public_property(session, row.property_id)
            if property_ is None:
                continue
            votes = list(
                session.scalars(
                    select(SharedPropertyVote).where(
                        SharedPropertyVote.shared_property_id == row.id
                    )
                )
            )
            comments = list(
                session.scalars(
                    select(SharedPropertyComment)
                    .where(SharedPropertyComment.shared_property_id == row.id)
                    .order_by(SharedPropertyComment.created_at)
                )
            )
            result.append(
                {
                    "id": row.id,
                    "property": self._property_facts(session, property_),
                    "added_by_user_id": row.added_by_user_id,
                    "created_at": row.created_at,
                    "votes": [
                        {"user_id": vote.user_id, "vote": vote.vote, "updated_at": vote.updated_at}
                        for vote in votes
                    ],
                    "comments": [
                        {
                            "id": comment.id,
                            "author_user_id": comment.author_user_id,
                            "body": comment.body,
                            "created_at": comment.created_at,
                        }
                        for comment in comments
                    ],
                }
            )
        return result

    def vote_for_property(
        self,
        session: Session,
        user_id: UUID,
        group_id: UUID,
        shared_property_id: UUID,
        body: SharedPropertyVoteInput,
    ) -> dict[str, object]:
        self._require_group_member(session, group_id, user_id)
        shared = session.get(SharedProperty, shared_property_id)
        if shared is None or shared.group_id != group_id:
            raise self.not_found("The shared property was not found.")
        vote = session.scalar(
            select(SharedPropertyVote).where(
                SharedPropertyVote.shared_property_id == shared.id,
                SharedPropertyVote.user_id == user_id,
            )
        )
        if vote is None:
            vote = SharedPropertyVote(shared_property_id=shared.id, user_id=user_id, vote=body.vote)
            session.add(vote)
        else:
            vote.vote = body.vote
            vote.updated_at = datetime.now(UTC)
        session.commit()
        return {"shared_property_id": shared.id, "vote": vote.vote, "updated_at": vote.updated_at}

    def comment_on_property(
        self,
        session: Session,
        user_id: UUID,
        group_id: UUID,
        shared_property_id: UUID,
        body: SharedPropertyCommentCreate,
    ) -> dict[str, object]:
        self._require_group_member(session, group_id, user_id)
        shared = session.get(SharedProperty, shared_property_id)
        if shared is None or shared.group_id != group_id:
            raise self.not_found("The shared property was not found.")
        row = SharedPropertyComment(
            shared_property_id=shared.id,
            author_user_id=user_id,
            body=body.body,
        )
        session.add(row)
        session.commit()
        return {
            "id": row.id,
            "author_user_id": row.author_user_id,
            "body": row.body,
            "created_at": row.created_at,
        }

    def create_task(
        self, session: Session, user_id: UUID, group_id: UUID, body: SharedTaskCreate
    ) -> SharedTask:
        self._require_group_member(session, group_id, user_id)
        if body.assigned_to_user_id is not None:
            self._require_group_member(session, group_id, body.assigned_to_user_id)
        row = SharedTask(
            group_id=group_id,
            created_by_user_id=user_id,
            assigned_to_user_id=body.assigned_to_user_id,
            title=body.title,
            details=body.details,
            due_at=body.due_at,
        )
        session.add(row)
        session.commit()
        return row

    def tasks(self, session: Session, user_id: UUID, group_id: UUID) -> list[SharedTask]:
        self._require_group_member(session, group_id, user_id)
        return list(
            session.scalars(
                select(SharedTask)
                .where(SharedTask.group_id == group_id)
                .order_by(SharedTask.due_at)
            )
        )

    def update_task(
        self,
        session: Session,
        user_id: UUID,
        group_id: UUID,
        task_id: UUID,
        body: SharedTaskUpdate,
    ) -> SharedTask:
        self._require_group_member(session, group_id, user_id)
        row = session.get(SharedTask, task_id)
        if row is None or row.group_id != group_id:
            raise self.not_found("The shared task was not found.")
        if user_id not in {row.created_by_user_id, row.assigned_to_user_id}:
            group = session.get(CollaborationGroup, group_id)
            membership = session.get(CollaborationGroupMember, (group_id, user_id))
            if membership is None or membership.role != "owner" or group is None:
                raise ApiError(
                    403,
                    "task_update_denied",
                    "Only the task owner, assignee, or group owner can update it.",
                )
        row.status = body.status
        row.updated_at = datetime.now(UTC)
        session.commit()
        return row

    def create_move_goal(
        self, session: Session, user_id: UUID, group_id: UUID, body: SharedMoveGoalCreate
    ) -> dict[str, object]:
        self._require_group_member(session, group_id, user_id)
        row = SharedMoveGoal(
            group_id=group_id,
            owner_user_id=user_id,
            title=body.title.strip(),
            target_date=body.target_date,
            encrypted_target_amount=None,
            amount_share_consented_at=(
                datetime.now(UTC)
                if body.share_amount_with_members and body.target_amount is not None
                else None
            ),
        )
        session.add(row)
        session.flush()
        if body.target_amount is not None:
            row.encrypted_target_amount = self.cipher.encrypt_amount(
                user_id, row.id, str(body.target_amount)
            )
        session.commit()
        return self._move_goal_response(session, row, user_id)

    def move_goals(
        self, session: Session, user_id: UUID, group_id: UUID
    ) -> list[dict[str, object]]:
        self._require_group_member(session, group_id, user_id)
        return [
            self._move_goal_response(session, row, user_id)
            for row in session.scalars(
                select(SharedMoveGoal)
                .where(SharedMoveGoal.group_id == group_id)
                .order_by(SharedMoveGoal.target_date)
            )
        ]

    def set_move_goal_financial_consent(
        self,
        session: Session,
        user_id: UUID,
        group_id: UUID,
        goal_id: UUID,
        body: SharedFinancialConsent,
    ) -> dict[str, object]:
        self._require_group_member(session, group_id, user_id)
        row = session.get(SharedMoveGoal, goal_id)
        if row is None or row.group_id != group_id or row.owner_user_id == user_id:
            raise self.not_found("The shared moving goal was not found.")
        consent = session.get(SharedMoveGoalConsent, (goal_id, user_id))
        if consent is None:
            consent = SharedMoveGoalConsent(goal_id=goal_id, user_id=user_id)
            session.add(consent)
        consent.consented_at = datetime.now(UTC) if body.consent_to_view_shared_amounts else None
        session.commit()
        return self._move_goal_response(session, row, user_id)

    def create_group_comparison(
        self, session: Session, user_id: UUID, group_id: UUID, body: SharedComparisonSave
    ) -> dict[str, object]:
        self._require_group_member(session, group_id, user_id)
        properties = [self._require_public_property(session, item) for item in body.property_ids]
        existing = set(
            session.scalars(
                select(SharedProperty.property_id).where(
                    SharedProperty.group_id == group_id,
                    SharedProperty.property_id.in_(body.property_ids),
                )
            )
        )
        if len(existing) != len(body.property_ids):
            raise ApiError(
                422,
                "comparison_requires_shared_homes",
                "Add each home to the group before comparing it.",
            )
        row = SharedComparison(
            group_id=group_id,
            created_by_user_id=user_id,
            name=body.name.strip(),
            property_ids=[str(item) for item in body.property_ids],
        )
        session.add(row)
        session.commit()
        return {
            "id": row.id,
            "name": row.name,
            "created_by_user_id": row.created_by_user_id,
            "created_at": row.created_at,
            "items": [self._property_facts(session, item) for item in properties],
        }

    def group_comparisons(
        self, session: Session, user_id: UUID, group_id: UUID
    ) -> list[dict[str, object]]:
        self._require_group_member(session, group_id, user_id)
        rows = list(
            session.scalars(
                select(SharedComparison)
                .where(SharedComparison.group_id == group_id)
                .order_by(SharedComparison.created_at.desc())
            )
        )
        result = []
        for row in rows:
            properties = [
                self._public_property(session, UUID(property_id))
                for property_id in row.property_ids
            ]
            result.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "created_by_user_id": row.created_by_user_id,
                    "created_at": row.created_at,
                    "items": [
                        self._property_facts(session, item)
                        for item in properties
                        if item is not None
                    ],
                }
            )
        return result

    def get_comparison_board(
        self, session: Session, user_id: UUID, board_id: UUID
    ) -> ComparisonBoardResponse:
        board = session.get(ComparisonBoard, board_id)
        if board is None or board.owner_user_id != user_id:
            raise self.not_found("The comparison was not found.")
        return self._comparison_response(session, board)

    def comparisons(self, session: Session, user_id: UUID) -> list[ComparisonBoardResponse]:
        rows = session.scalars(
            select(ComparisonBoard)
            .where(ComparisonBoard.owner_user_id == user_id)
            .order_by(ComparisonBoard.updated_at.desc())
        )
        return [self._comparison_response(session, row) for row in rows]

    def create_comparison(
        self, session: Session, user_id: UUID, body: ComparisonBoardSave
    ) -> ComparisonBoardResponse:
        self._permission(session, user_id, "property:compare:public", scope="public", scope_id="*")
        properties = [
            self._require_public_property(session, item.property_id) for item in body.items
        ]
        board = ComparisonBoard(owner_user_id=user_id, name=body.name)
        session.add(board)
        session.flush()
        for position, (item, property_) in enumerate(zip(body.items, properties, strict=True)):
            data = {
                "note": item.note,
                "monthly_cost_input": str(item.monthly_cost_input)
                if item.monthly_cost_input is not None
                else None,
                "move_in_cost_input": str(item.move_in_cost_input)
                if item.move_in_cost_input is not None
                else None,
            }
            session.add(
                ComparisonItem(
                    board_id=board.id,
                    property_id=property_.id,
                    position=position,
                    encrypted_user_data=self.cipher.encrypt_json(
                        "comparison_item", user_id, property_.id, data
                    ),
                )
            )
        session.commit()
        return self._comparison_response(session, board)

    def update_comparison(
        self, session: Session, user_id: UUID, board_id: UUID, body: ComparisonBoardSave
    ) -> ComparisonBoardResponse:
        board = session.get(ComparisonBoard, board_id)
        if board is None or board.owner_user_id != user_id:
            raise self.not_found("The comparison was not found.")
        properties = [
            self._require_public_property(session, item.property_id) for item in body.items
        ]
        for row in list(
            session.scalars(select(ComparisonItem).where(ComparisonItem.board_id == board.id))
        ):
            session.delete(row)
        session.flush()
        for position, (item, property_) in enumerate(zip(body.items, properties, strict=True)):
            data = {
                "note": item.note,
                "monthly_cost_input": str(item.monthly_cost_input)
                if item.monthly_cost_input is not None
                else None,
                "move_in_cost_input": str(item.move_in_cost_input)
                if item.move_in_cost_input is not None
                else None,
            }
            session.add(
                ComparisonItem(
                    board_id=board.id,
                    property_id=property_.id,
                    position=position,
                    encrypted_user_data=self.cipher.encrypt_json(
                        "comparison_item", user_id, property_.id, data
                    ),
                )
            )
        board.name = body.name
        board.updated_at = datetime.now(UTC)
        session.commit()
        return self._comparison_response(session, board)

    def delete_comparison(self, session: Session, user_id: UUID, board_id: UUID) -> None:
        board = session.get(ComparisonBoard, board_id)
        if board is None or board.owner_user_id != user_id:
            raise self.not_found("The comparison was not found.")
        session.delete(board)
        session.commit()

    def save_roommate_profile(
        self, session: Session, user_id: UUID, body: RoommateProfileSave
    ) -> RoommateProfileResponse:
        self._permission(
            session, user_id, "roommate:manage:self", scope="user", scope_id=str(user_id)
        )
        if body.county_id is not None and session.get(County, body.county_id) is None:
            raise ApiError(
                422, "location_not_found", "Choose a Kenyan county from the location list."
            )
        if body.town_id is not None:
            town = session.get(Town, body.town_id)
            if town is None or (body.county_id is not None and town.county_id != body.county_id):
                raise ApiError(422, "location_not_found", "Choose a town in the selected county.")
        row = session.scalar(select(RoommateProfile).where(RoommateProfile.user_id == user_id))
        if row is None:
            row = RoommateProfile(user_id=user_id, display_alias=body.display_alias)
            session.add(row)
        for field in (
            "display_alias",
            "about",
            "budget_min",
            "budget_max",
            "county_id",
            "town_id",
            "preferred_move_in",
            "lifestyle_tags",
            "matching_enabled",
        ):
            setattr(row, field, getattr(body, field))
        row.updated_at = datetime.now(UTC)
        session.commit()
        return self._roommate_profile_response(row)

    def my_roommate_profile(
        self, session: Session, user_id: UUID
    ) -> RoommateProfileResponse | None:
        row = session.scalar(select(RoommateProfile).where(RoommateProfile.user_id == user_id))
        return self._roommate_profile_response(row) if row else None

    def roommate_suggestions(
        self,
        session: Session,
        user_id: UUID,
        *,
        county_id: UUID | None,
        town_id: UUID | None,
        budget_max: Decimal | None,
    ) -> list[RoommateCandidateResponse]:
        self._permission(session, user_id, "roommate:search:public", scope="public", scope_id="*")
        own = session.scalar(select(RoommateProfile).where(RoommateProfile.user_id == user_id))
        statement = select(RoommateProfile).where(
            RoommateProfile.matching_enabled.is_(True), RoommateProfile.user_id != user_id
        )
        if county_id:
            statement = statement.where(RoommateProfile.county_id == county_id)
        elif town_id:
            statement = statement.where(RoommateProfile.town_id == town_id)
        if budget_max is not None:
            statement = statement.where(
                or_(RoommateProfile.budget_min.is_(None), RoommateProfile.budget_min <= budget_max)
            )
        rows = list(session.scalars(statement.limit(100)))
        ranked = sorted(rows, key=lambda row: (-self._match_score(own, row), row.created_at))[:30]
        results = []
        for row in ranked:
            county = session.get(County, row.county_id) if row.county_id else None
            town = session.get(Town, row.town_id) if row.town_id else None
            shared_tags = sorted(set(own.lifestyle_tags if own else []) & set(row.lifestyle_tags))
            results.append(
                RoommateCandidateResponse(
                    profile_id=row.id,
                    display_alias=row.display_alias,
                    about=row.about,
                    budget_min=row.budget_min,
                    budget_max=row.budget_max,
                    county_id=row.county_id,
                    county_name=county.name if county else None,
                    town_id=row.town_id,
                    town_name=town.name if town else None,
                    preferred_move_in=row.preferred_move_in,
                    lifestyle_tags=row.lifestyle_tags,
                    shared_preferences=shared_tags,
                )
            )
        return results

    def roommate_interest(
        self, session: Session, user_id: UUID, profile_id: UUID
    ) -> RoommateInterestResponse:
        self._permission(session, user_id, "roommate:connect:public", scope="public", scope_id="*")
        profile = session.get(RoommateProfile, profile_id)
        if profile is None or not profile.matching_enabled or profile.user_id == user_id:
            raise self.not_found("The roommate profile was not found.")
        account = session.get(UserAccount, profile.user_id)
        if account is None or account.status != "active":
            raise self.not_found("The roommate profile was not found.")
        row = session.scalar(
            select(RoommateInterest).where(
                RoommateInterest.requester_user_id == user_id,
                RoommateInterest.target_user_id == profile.user_id,
            )
        )
        if row is None:
            row = RoommateInterest(requester_user_id=user_id, target_user_id=profile.user_id)
            session.add(row)
        elif row.status in {"declined", "withdrawn"}:
            row.status = "pending"
            row.updated_at = datetime.now(UTC)
        else:
            raise ApiError(409, "roommate_interest_exists", "A roommate request is already active.")
        session.add(
            InAppNotification(
                recipient_user_id=profile.user_id,
                category="roommate_interest",
                title="Roommate connection request",
                body="A HomeScout member would like to connect about shared housing.",
                target_path="/collaboration?tab=Roommates",
            )
        )
        session.commit()
        return self._interest_response(row, profile.id)

    def roommate_interests(self, session: Session, user_id: UUID) -> list[RoommateInterestResponse]:
        rows = list(
            session.scalars(
                select(RoommateInterest)
                .where(
                    or_(
                        RoommateInterest.requester_user_id == user_id,
                        RoommateInterest.target_user_id == user_id,
                    )
                )
                .order_by(RoommateInterest.updated_at.desc())
            )
        )
        result = []
        for row in rows:
            profile = session.scalar(
                select(RoommateProfile).where(RoommateProfile.user_id == row.target_user_id)
            )
            profile_id = profile.id if profile else UUID(int=0)
            result.append(self._interest_response(row, profile_id))
        return result

    def decide_roommate_interest(
        self,
        session: Session,
        user_id: UUID,
        interest_id: UUID,
        body: RoommateInterestDecision,
    ) -> RoommateInterestResponse:
        row = session.get(RoommateInterest, interest_id)
        if row is None or row.target_user_id != user_id or row.status != "pending":
            raise self.not_found("The roommate request was not found.")
        row.status = "accepted" if body.accept else "declined"
        row.updated_at = datetime.now(UTC)
        profile = session.scalar(select(RoommateProfile).where(RoommateProfile.user_id == user_id))
        if body.accept:
            session.add(
                InAppNotification(
                    recipient_user_id=row.requester_user_id,
                    category="roommate_interest",
                    title="Roommate connection accepted",
                    body="Your HomeScout roommate connection request was accepted.",
                    target_path="/collaboration?tab=Roommates",
                )
            )
            conversation = session.scalar(
                select(Conversation).where(Conversation.roommate_interest_id == row.id)
            )
            if conversation is None:
                conversation = Conversation(roommate_interest_id=row.id, created_by_user_id=user_id)
                session.add(conversation)
                session.flush()
                session.add_all(
                    [
                        ConversationParticipant(
                            conversation_id=conversation.id, user_id=row.requester_user_id
                        ),
                        ConversationParticipant(
                            conversation_id=conversation.id, user_id=row.target_user_id
                        ),
                    ]
                )
        session.commit()
        return self._interest_response(row, profile.id if profile else UUID(int=0))

    def _invite_account(
        self, session: Session, group: CollaborationGroup, inviter_id: UUID, invitee_id: UUID
    ) -> None:
        if inviter_id == invitee_id:
            raise ApiError(422, "cannot_invite_self", "You are already in this group.")
        account = session.get(UserAccount, invitee_id)
        if account is None or account.status != "active":
            raise self.not_found("The account was not found.")
        members = (
            session.scalar(
                select(func.count())
                .select_from(CollaborationGroupMember)
                .where(
                    CollaborationGroupMember.group_id == group.id,
                    CollaborationGroupMember.status.in_(("invited", "active")),
                )
            )
            or 0
        )
        if members >= 20:
            raise ApiError(
                409, "group_member_limit", "A shared search group can have up to 20 members."
            )
        existing = session.get(CollaborationGroupMember, (group.id, invitee_id))
        if existing is not None and existing.status in {"active", "invited"}:
            raise ApiError(
                409, "group_invitation_exists", "This account is already a member or invitee."
            )
        if existing is None:
            existing = CollaborationGroupMember(
                group_id=group.id,
                user_id=invitee_id,
                invited_by_user_id=inviter_id,
                role="member",
                status="invited",
            )
            session.add(existing)
        else:
            existing.invited_by_user_id = inviter_id
            existing.status = "invited"
            existing.responded_at = None
        session.add(
            InAppNotification(
                recipient_user_id=invitee_id,
                category="shared_group_invitation",
                title="HomeScout shared search invitation",
                body="You have an invitation to join a HomeScout shared search group.",
                target_path="/collaboration?tab=Groups",
            )
        )

    def _require_group_member(
        self, session: Session, group_id: UUID, user_id: UUID
    ) -> CollaborationGroupMember:
        membership = session.get(CollaborationGroupMember, (group_id, user_id))
        if membership is None or membership.status != "active":
            raise self.not_found("The shared group was not found.")
        self._permission(
            session, user_id, "shared_group:view:member", scope="group", scope_id=str(group_id)
        )
        return membership

    def _require_group_owner(
        self, session: Session, group_id: UUID, user_id: UUID
    ) -> CollaborationGroup:
        group = session.get(CollaborationGroup, group_id)
        membership = session.get(CollaborationGroupMember, (group_id, user_id))
        if (
            group is None
            or membership is None
            or membership.status != "active"
            or membership.role != "owner"
        ):
            raise self.not_found("The shared group was not found.")
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code="shared_group:manage:owned",
            resource_owner_id=group.created_by_user_id,
            resource_scope_type="group",
            resource_scope_id=str(group_id),
        )
        return group

    def _group_response(
        self, session: Session, group: CollaborationGroup | None, user_id: UUID
    ) -> GroupResponse:
        if group is None:
            raise self.not_found("The shared group was not found.")
        own = session.get(CollaborationGroupMember, (group.id, user_id))
        if own is None or own.status not in {"active", "invited"}:
            raise self.not_found("The shared group was not found.")
        memberships = list(
            session.scalars(
                select(CollaborationGroupMember)
                .where(CollaborationGroupMember.group_id == group.id)
                .order_by(CollaborationGroupMember.created_at)
            )
        )
        if own.status == "invited":
            memberships = [
                member
                for member in memberships
                if member.user_id in {user_id, group.created_by_user_id}
            ]
        return GroupResponse(
            id=group.id,
            name=group.name,
            created_by_user_id=group.created_by_user_id,
            status=own.status,
            members=[
                GroupMemberResponse(
                    user_id=member.user_id,
                    role=member.role,
                    status=member.status,
                    created_at=member.created_at,
                    responded_at=member.responded_at,
                )
                for member in memberships
            ],
            created_at=group.created_at,
            updated_at=group.updated_at,
        )

    def _move_goal_response(
        self, session: Session, row: SharedMoveGoal, viewer_id: UUID
    ) -> dict[str, object]:
        amount = None
        consent = session.get(SharedMoveGoalConsent, (row.id, viewer_id))
        if (
            row.encrypted_target_amount is not None
            and row.amount_share_consented_at is not None
            and (
                viewer_id == row.owner_user_id
                or (consent is not None and consent.consented_at is not None)
            )
        ):
            amount = self.cipher.decrypt_amount(
                row.owner_user_id, row.id, row.encrypted_target_amount
            )
        return {
            "id": row.id,
            "group_id": row.group_id,
            "owner_user_id": row.owner_user_id,
            "title": row.title,
            "target_date": row.target_date,
            "target_amount_kes": amount,
            "amount_shared_by_owner": row.amount_share_consented_at is not None,
            "viewer_has_consented": viewer_id == row.owner_user_id
            or (consent is not None and consent.consented_at is not None),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _comparison_response(
        self, session: Session, board: ComparisonBoard
    ) -> ComparisonBoardResponse:
        items = []
        for item in session.scalars(
            select(ComparisonItem)
            .where(ComparisonItem.board_id == board.id)
            .order_by(ComparisonItem.position)
        ):
            property_ = self._public_property(session, item.property_id)
            if property_ is None:
                continue
            private = (
                self.cipher.decrypt_json(
                    "comparison_item", board.owner_user_id, property_.id, item.encrypted_user_data
                )
                if item.encrypted_user_data
                else {}
            )
            facts = self._property_facts(session, property_)
            rent = property_.rent_amount if property_.rent_frequency == "monthly" else None
            deposit = property_.deposit_amount
            known_move_in = rent + deposit if rent is not None and deposit is not None else None
            extra_monthly = (
                Decimal(private["monthly_cost_input"])
                if private.get("monthly_cost_input")
                else None
            )
            extra_move_in = (
                Decimal(private["move_in_cost_input"])
                if private.get("move_in_cost_input")
                else None
            )
            facts.update(
                {
                    "user_note": private.get("note"),
                    "user_monthly_cost_input_kes": extra_monthly,
                    "user_move_in_cost_input_kes": extra_move_in,
                    "known_monthly_cost_kes": rent,
                    "known_move_in_cost_kes": known_move_in,
                    "estimated_monthly_total_kes": rent + extra_monthly
                    if rent is not None and extra_monthly is not None
                    else rent,
                    "estimated_move_in_total_kes": known_move_in + extra_move_in
                    if known_move_in is not None and extra_move_in is not None
                    else known_move_in,
                    "cost_estimate_note": (
                        "Listing figures are source records; extra costs are your own estimates."
                    ),
                    "transport_information": None,
                }
            )
            items.append(facts)
        return ComparisonBoardResponse(
            id=board.id,
            owner_user_id=board.owner_user_id,
            name=board.name,
            items=items,
            created_at=board.created_at,
            updated_at=board.updated_at,
        )

    @staticmethod
    def _property_facts(session: Session, property_: Property) -> dict[str, object]:
        county = session.get(County, property_.county_id)
        town = session.get(Town, property_.town_id)
        amenities = list(
            session.scalars(
                select(PropertyAmenity.amenity).where(PropertyAmenity.property_id == property_.id)
            )
        )
        return {
            "property_id": property_.id,
            "title": property_.title,
            "rent_amount_kes": property_.rent_amount,
            "rent_frequency": property_.rent_frequency,
            "deposit_amount_kes": property_.deposit_amount,
            "county": county.name if county else None,
            "town": town.name if town else None,
            "bedrooms": property_.bedrooms,
            "bathrooms": property_.bathrooms,
            "size_sqm": property_.size_sqm,
            "amenities": amenities or property_.amenities,
            "furnishing": property_.furnishing,
            "security_information": property_.security_features or None,
            "utilities": {
                "water_availability": property_.water_availability,
                "electricity_available": property_.electricity_available,
                "internet_available": property_.internet_available,
            },
            "verification_status": property_.verification_status,
            "availability_status": property_.availability_status,
            "currency": "KES",
        }

    @staticmethod
    def _public_property(session: Session, property_id: UUID) -> Property | None:
        return session.scalar(
            select(Property).where(
                Property.id == property_id,
                Property.listing_status == "published",
                Property.availability_status == "available",
                Property.moderation_status == "clear",
                Property.is_demo.is_(False),
            )
        )

    def _require_public_property(self, session: Session, property_id: UUID) -> Property:
        row = self._public_property(session, property_id)
        if row is None:
            raise ApiError(404, "property_not_found", "The available property was not found.")
        return row

    def _roommate_profile_response(self, row: RoommateProfile) -> RoommateProfileResponse:
        return RoommateProfileResponse(
            id=row.id,
            display_alias=row.display_alias,
            about=row.about,
            budget_min=row.budget_min,
            budget_max=row.budget_max,
            county_id=row.county_id,
            town_id=row.town_id,
            preferred_move_in=row.preferred_move_in,
            lifestyle_tags=row.lifestyle_tags,
            matching_enabled=row.matching_enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _match_score(first: RoommateProfile | None, second: RoommateProfile) -> int:
        if first is None:
            return 0
        score = 0
        if first.town_id and first.town_id == second.town_id:
            score += 5
        elif first.county_id and first.county_id == second.county_id:
            score += 3
        if (
            first.budget_min is not None
            and first.budget_max is not None
            and second.budget_min is not None
            and second.budget_max is not None
            and max(first.budget_min, second.budget_min) <= min(first.budget_max, second.budget_max)
        ):
            score += 4
        if first.preferred_move_in and second.preferred_move_in:
            if abs((first.preferred_move_in - second.preferred_move_in).days) <= 45:
                score += 2
        score += len(set(first.lifestyle_tags) & set(second.lifestyle_tags))
        return score

    @staticmethod
    def _interest_response(row: RoommateInterest, profile_id: UUID) -> RoommateInterestResponse:
        return RoommateInterestResponse(
            id=row.id,
            profile_id=profile_id,
            requester_user_id=row.requester_user_id,
            target_user_id=row.target_user_id,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _permission(
        self, session: Session, user_id: UUID, code: str, *, scope: str, scope_id: str
    ) -> None:
        self.authorization.require_permission(
            session,
            user_id=user_id,
            permission_code=code,
            resource_owner_id=user_id if code.endswith(":self") else None,
            resource_scope_type=scope,
            resource_scope_id=scope_id,
        )

    @staticmethod
    def not_found(message: str) -> ApiError:
        return ApiError(404, "collaboration_item_not_found", message)
