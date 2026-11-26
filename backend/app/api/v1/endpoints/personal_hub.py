"""Authenticated, owner-scoped HomeScout personal hub APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.data_access.personal_hub import PersonalHubDataAccess
from app.models.access_control import Role, UserRoleAssignment
from app.models.notification import InAppNotification
from app.models.personal_hub import (
    AccountDeletionRequest,
    CollectionShare,
    ManualRecord,
    PersonalActivity,
    PrivateDocument,
    SavedCollection,
    SavedHubItem,
    ScheduleEntry,
    SupportTicket,
    UserPreference,
)
from app.models.user import UserAccount, UserProfile
from app.schemas.personal_hub import (
    ActiveRoleUpdate,
    ActivityCreate,
    ActivityResponse,
    CollectionCreate,
    CollectionResponse,
    CollectionShareCreate,
    CollectionUpdate,
    DeletionRequestCreate,
    DeletionRequestResponse,
    DocumentResponse,
    ManualRecordCreate,
    ManualRecordResponse,
    NotificationResponse,
    PreferenceResponse,
    PreferenceUpdate,
    ProfileResponse,
    ProfileUpdate,
    SavedItemCreate,
    SavedItemResponse,
    SavedItemUpdate,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    SupportMessageCreate,
    SupportTicketCreate,
    SupportTicketResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.media_storage import LocalMediaStorage
from app.services.personal_hub import PersonalHubService
from app.services.trust_cipher import TrustCipher

router = APIRouter(prefix="/hub", tags=["personal hub"])
service = PersonalHubService()
data = PersonalHubDataAccess()

HELP_ARTICLES = [
    {
        "slug": "safe-search",
        "title": "Search safely for a home",
        "category": "safety",
        "body": (
            "Meet at the property where practical, confirm details independently, and do not send "
            "money before you understand the agreement."
        ),
    },
    {
        "slug": "account-security",
        "title": "Protect your account",
        "category": "account",
        "body": (
            "Use a unique password, review active sessions, and sign out sessions you do not "
            "recognize."
        ),
    },
    {
        "slug": "demo-listings",
        "title": "Understand sample listings",
        "category": "properties",
        "body": (
            "Sample homes are illustrative only. They are not available, verified, or real "
            "HomeScout listings."
        ),
    },
    {
        "slug": "manual-records",
        "title": "About personal records",
        "category": "records",
        "body": (
            "Records you add are private notes. They do not represent a payment processed or "
            "confirmed by HomeScout."
        ),
    },
    {
        "slug": "notifications",
        "title": "In-app notifications",
        "category": "settings",
        "body": (
            "Notifications shown in HomeScout are stored in the app. Email and push delivery "
            "are not configured."
        ),
    },
]


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    user, preference = service.profile(session, principal.user_id)
    profile = user.profile
    roles = list(
        session.scalars(
            select(Role.code)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user.id)
            .order_by(Role.code)
        )
    )
    return ProfileResponse(
        id=user.id,
        given_name=profile.given_name if profile else None,
        family_name=profile.family_name if profile else None,
        preferred_name=profile.preferred_name if profile else None,
        requested_role_code=profile.requested_role_code if profile else None,
        email=user.email,
        phone_number=user.phone_number,
        location_label=profile.location_label if profile else None,
        bio=profile.bio if profile else None,
        profile_photo_available=bool(profile and profile.profile_image_key),
        roles=roles,
        active_role_code=preference.active_role_code,
        email_verified=user.email_verified_at is not None,
        phone_verified=user.phone_verified_at is not None,
    )


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    service.update_profile(session, principal.user_id, body)
    return get_profile(principal, session)


@router.put("/profile/active-role", response_model=PreferenceResponse)
def set_active_role(
    body: ActiveRoleUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PreferenceResponse:
    return _preference_response(service.set_active_role(session, principal.user_id, body.role_code))


@router.get("/preferences", response_model=PreferenceResponse)
def get_preferences(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PreferenceResponse:
    return _preference_response(service.preferences(session, principal.user_id))


@router.patch("/preferences", response_model=PreferenceResponse)
def update_preferences(
    body: PreferenceUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PreferenceResponse:
    return _preference_response(service.update_preferences(session, principal.user_id, body))


@router.post("/profile/photo", response_model=ProfileResponse)
async def upload_profile_photo(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    filename: str = Query(default="profile-photo"),
) -> ProfileResponse:
    contents = await _read_limited(request, min(settings.private_document_max_bytes, 5_242_880))
    content_type, extension = _image_type(contents)
    if content_type is None or len(contents) > min(settings.private_document_max_bytes, 5_242_880):
        raise ApiError(
            422, "invalid_profile_photo", "Upload a JPEG, PNG, or WebP image up to 5 MB."
        )
    user = session.get(UserAccount, principal.user_id)
    if user is None:
        raise ApiError(404, "profile_not_found", "The profile was not found.")
    if user.profile is None:
        user.profile = UserProfile(user_id=user.id)
    key = f"{uuid.uuid4().hex}{extension}"
    storage = LocalMediaStorage(settings.private_document_storage_dir)
    storage.put(key, contents)
    previous = user.profile.profile_image_key
    user.profile.profile_image_key = key
    session.commit()
    if previous:
        storage.delete(previous)
    return get_profile(principal, session)


@router.get("/profile/photo")
def get_profile_photo(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    user = session.get(UserAccount, principal.user_id)
    key = user.profile.profile_image_key if user and user.profile else None
    if not key:
        raise ApiError(404, "photo_not_found", "No profile photo is available.")
    file_path = LocalMediaStorage(settings.private_document_storage_dir).get(key)
    if file_path is None:
        raise ApiError(404, "photo_not_found", "No profile photo is available.")
    mime = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(
        file_path.suffix, "application/octet-stream"
    )
    return FileResponse(
        file_path,
        media_type=mime,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/saved", response_model=list[SavedItemResponse])
def saved_items(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[SavedHubItem]:
    return data.saved_items(session, principal.user_id)


@router.post("/saved", response_model=SavedItemResponse, status_code=201)
def create_saved_item(
    body: SavedItemCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> SavedHubItem:
    return service.save_item(session, principal.user_id, body)


@router.patch("/saved/{item_id}", response_model=SavedItemResponse)
def update_saved_item(
    item_id: UUID,
    body: SavedItemUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> SavedHubItem:
    return service.update_saved_item(session, principal.user_id, item_id, body)


@router.delete("/saved/{item_id}", status_code=204)
def delete_saved_item(
    item_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    row = session.get(SavedHubItem, item_id)
    if row is None or not service.can_edit_saved_item(session, principal.user_id, row):
        raise service._not_found()
    session.delete(row)
    session.commit()
    return Response(status_code=204)


@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[CollectionResponse]:
    return [
        _collection_response(session, principal.user_id, row)
        for row in data.collections(session, principal.user_id)
    ]


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> CollectionResponse:
    row = service.require_collection_access(session, principal.user_id, collection_id)
    return _collection_response(session, principal.user_id, row)


@router.post("/collections", response_model=CollectionResponse, status_code=201)
def create_collection(
    body: CollectionCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> CollectionResponse:
    row = service.create_collection(session, principal.user_id, body)
    return _collection_response(session, principal.user_id, row)


@router.get("/collections/{collection_id}/items", response_model=list[SavedItemResponse])
def collection_items(
    collection_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[SavedHubItem]:
    service.require_collection_access(session, principal.user_id, collection_id)
    return data.collection_items(session, collection_id)


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: UUID,
    body: CollectionUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> CollectionResponse:
    row = service.update_collection(session, principal.user_id, collection_id, body)
    return _collection_response(session, principal.user_id, row)


@router.post("/collections/{collection_id}/share", status_code=204)
def share_collection(
    collection_id: UUID,
    body: CollectionShareCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.share_collection(session, principal.user_id, collection_id, body)
    return Response(status_code=204)


@router.delete("/collections/{collection_id}/share/{user_id}", status_code=204)
def unshare_collection(
    collection_id: UUID,
    user_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    collection = session.get(SavedCollection, collection_id)
    if collection is None or collection.owner_user_id != principal.user_id:
        raise service._not_found()
    share = session.get(CollectionShare, (collection_id, user_id))
    if share:
        session.delete(share)
        session.commit()
    return Response(status_code=204)


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(
    collection_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    collection = session.get(SavedCollection, collection_id)
    if collection is None or collection.owner_user_id != principal.user_id:
        raise service._not_found()
    session.delete(collection)
    session.commit()
    return Response(status_code=204)


@router.get("/activity", response_model=list[ActivityResponse])
def activity(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    event_type: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=200),
    after: datetime | None = None,
    before: datetime | None = None,
) -> list[PersonalActivity]:
    if (after and after.tzinfo is None) or (before and before.tzinfo is None):
        raise ApiError(422, "invalid_date_range", "Date filters must include timezone offsets.")
    rows = data.activity(session, principal.user_id, event_type, min(limit * 3, 500))
    lower = after.astimezone(UTC) if after else None
    upper = before.astimezone(UTC) if before else None
    return [
        row
        for row in rows
        if (lower is None or _as_utc(row.created_at) >= lower)
        and (upper is None or _as_utc(row.created_at) < upper)
    ][:limit]


@router.post("/activity", response_model=ActivityResponse, status_code=201)
def add_activity(
    body: ActivityCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PersonalActivity:
    return service.add_activity(session, principal.user_id, body)


@router.delete("/activity", status_code=204)
def clear_activity(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    rows = list(
        session.scalars(
            select(PersonalActivity).where(PersonalActivity.owner_user_id == principal.user_id)
        )
    )
    for row in rows:
        session.delete(row)
    session.commit()
    return Response(status_code=204)


@router.get("/schedule", response_model=list[ScheduleResponse])
def schedule(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    after: datetime | None = None,
    before: datetime | None = None,
) -> list[ScheduleEntry]:
    if (after and after.tzinfo is None) or (before and before.tzinfo is None):
        raise ApiError(422, "invalid_date_range", "Schedule filters must include timezone offsets.")
    return data.schedule(
        session,
        principal.user_id,
        after.astimezone(UTC) if after else None,
        before.astimezone(UTC) if before else None,
    )


@router.post("/schedule", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    body: ScheduleCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleEntry:
    return service.create_schedule(session, principal.user_id, body)


@router.patch("/schedule/{entry_id}", response_model=ScheduleResponse)
def update_schedule(
    entry_id: UUID,
    body: ScheduleUpdate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ScheduleEntry:
    return service.update_schedule(session, principal.user_id, entry_id, body)


@router.delete("/schedule/{entry_id}", status_code=204)
def delete_schedule(
    entry_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.delete_schedule(session, principal.user_id, entry_id)
    return Response(status_code=204)


@router.get("/notifications", response_model=list[NotificationResponse])
def notifications(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    category: str | None = Query(default=None, max_length=64),
    unread_only: bool = False,
) -> list[InAppNotification]:
    return data.notifications(session, principal.user_id, category, unread_only)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> InAppNotification:
    return service.mark_notification(session, principal.user_id, notification_id, dismiss=False)


@router.post("/notifications/read-all")
def read_all_notifications(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, int]:
    return {"updated": service.mark_all_notifications_read(session, principal.user_id)}


@router.post("/notifications/{notification_id}/dismiss", response_model=NotificationResponse)
def dismiss_notification(
    notification_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> InAppNotification:
    return service.mark_notification(session, principal.user_id, notification_id, dismiss=True)


@router.get("/records", response_model=list[ManualRecordResponse])
def manual_records(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[ManualRecord]:
    return data.manual_records(session, principal.user_id)


@router.post("/records", response_model=ManualRecordResponse, status_code=201)
def create_manual_record(
    body: ManualRecordCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> ManualRecord:
    return service.add_manual_record(session, principal.user_id, body)


@router.get("/documents", response_model=list[DocumentResponse])
def documents(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PrivateDocument]:
    return data.documents(session, principal.user_id)


@router.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    category: str = Query(
        pattern="^(agreement|receipt|inspection|checklist|moving|verification|other)$"
    ),
    filename: str = Query(default="document", max_length=240),
) -> PrivateDocument:
    contents = await _read_limited(request, settings.private_document_max_bytes)
    content_type, extension = _document_type(contents)
    if len(contents) > settings.private_document_max_bytes or content_type is None:
        raise ApiError(
            422,
            "invalid_document",
            "Upload a PDF, JPEG, PNG, or WebP document within the size limit.",
        )
    document_id = uuid.uuid4()
    key = f"{document_id.hex}{extension}"
    row = PrivateDocument(
        id=document_id,
        owner_user_id=principal.user_id,
        storage_key=key,
        original_filename=service.clean_filename(filename),
        content_type=content_type,
        size_bytes=len(contents),
        category=category,
        storage_encrypted=category == "verification",
    )
    stored_contents = (
        TrustCipher(settings).encrypt_document(principal.user_id, document_id, contents)
        if category == "verification"
        else contents
    )
    LocalMediaStorage(settings.private_document_storage_dir).put(key, stored_contents)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    row = session.get(PrivateDocument, document_id)
    if row is None or row.owner_user_id != principal.user_id:
        raise service._not_found()
    file_path = LocalMediaStorage(settings.private_document_storage_dir).get(row.storage_key)
    if file_path is None:
        raise ApiError(404, "document_missing", "The private document file is no longer available.")
    if row.storage_encrypted:
        contents = TrustCipher(settings).decrypt_document(
            row.owner_user_id, row.id, file_path.read_bytes()
        )
        return Response(
            content=contents,
            media_type=row.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{row.original_filename}"',
                "Cache-Control": "private, no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
    return FileResponse(
        file_path,
        media_type=row.content_type,
        filename=row.original_filename,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    row = session.get(PrivateDocument, document_id)
    if row is None or row.owner_user_id != principal.user_id:
        raise service._not_found()
    key = row.storage_key
    session.delete(row)
    session.commit()
    LocalMediaStorage(settings.private_document_storage_dir).delete(key)
    return Response(status_code=204)


@router.get("/support/articles")
def help_articles(q: str | None = Query(default=None, max_length=80)) -> list[dict[str, str]]:
    query = (q or "").strip().casefold()
    return [
        article
        for article in HELP_ARTICLES
        if not query or query in " ".join(article.values()).casefold()
    ]


@router.get("/support/tickets", response_model=list[SupportTicketResponse])
def support_tickets(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[SupportTicket]:
    return data.tickets(session, principal.user_id)


@router.post("/support/tickets", response_model=SupportTicketResponse, status_code=201)
def create_support_ticket(
    body: SupportTicketCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> SupportTicket:
    return service.create_ticket(session, principal.user_id, body)


@router.post("/support/tickets/{ticket_id}/messages", response_model=SupportTicketResponse)
def reply_to_support_ticket(
    ticket_id: UUID,
    body: SupportMessageCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> SupportTicket:
    return service.add_ticket_message(session, principal.user_id, ticket_id, body)


@router.get("/account/deletion-requests", response_model=list[DeletionRequestResponse])
def deletion_requests(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[AccountDeletionRequest]:
    return data.deletion_requests(session, principal.user_id)


@router.post("/account/deletion-requests", response_model=DeletionRequestResponse, status_code=202)
def create_deletion_request(
    body: DeletionRequestCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> AccountDeletionRequest:
    return service.create_deletion_request(session, principal.user_id, body)


@router.delete("/account/deletion-requests/{request_id}", response_model=DeletionRequestResponse)
def cancel_deletion_request(
    request_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> AccountDeletionRequest:
    return service.cancel_deletion_request(session, principal.user_id, request_id)


@router.get("/account/export")
def export_account_data(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
):
    user, preference = service.profile(session, principal.user_id)
    profile = user.profile
    return {
        "product": "HomeScout",
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": {
            "email": user.email,
            "phone_number": user.phone_number,
            "given_name": profile.given_name if profile else None,
            "family_name": profile.family_name if profile else None,
            "preferred_name": profile.preferred_name if profile else None,
            "location_label": profile.location_label if profile else None,
            "bio": profile.bio if profile else None,
        },
        "preferences": _preference_response(preference).model_dump(),
        "saved_items": [
            SavedItemResponse.model_validate(row).model_dump()
            for row in data.saved_items(session, principal.user_id)
        ],
        "saved_property_ids": [
            {"property_id": str(row.property_id), "created_at": row.created_at}
            for row in data.marketplace_saves(session, principal.user_id)
        ],
        "search_history": [
            {
                "filters": row.filters,
                "result_count": row.result_count,
                "created_at": row.created_at,
            }
            for row in data.search_history(session, principal.user_id)
        ],
        "saved_search_alerts": [
            {
                "id": str(row.id),
                "filters": row.filters,
                "is_active": row.is_active,
                "created_at": row.created_at,
            }
            for row in data.alerts(session, principal.user_id)
        ],
        "activity": [
            ActivityResponse.model_validate(row).model_dump()
            for row in data.activity(session, principal.user_id, None, 200)
        ],
        "schedule": [
            ScheduleResponse.model_validate(row).model_dump()
            for row in data.schedule(session, principal.user_id, None, None)
        ],
        "manual_records": [
            ManualRecordResponse.model_validate(row).model_dump()
            for row in data.manual_records(session, principal.user_id)
        ],
        "documents": [
            DocumentResponse.model_validate(row).model_dump()
            for row in data.documents(session, principal.user_id)
        ],
        "notifications": [
            {
                "id": str(row.id),
                "category": row.category,
                "title": row.title,
                "body": row.body,
                "created_at": row.created_at,
                "read_at": row.read_at,
                "dismissed_at": row.dismissed_at,
            }
            for row in data.notifications_for_export(session, principal.user_id)
        ],
        "support_tickets": [
            SupportTicketResponse.model_validate(row).model_dump()
            for row in data.tickets(session, principal.user_id)
        ],
        "account_deletion_requests": [
            DeletionRequestResponse.model_validate(row).model_dump()
            for row in data.deletion_requests(session, principal.user_id)
        ],
        "notes": (
            "Manual records are user-entered and do not prove payments. "
            "Notifications are in-app only."
        ),
    }


def _preference_response(row: UserPreference) -> PreferenceResponse:
    return PreferenceResponse(
        appearance=row.appearance,
        active_role_code=row.active_role_code,
        notification_preferences=row.notification_preferences or {},
        accessibility_preferences=row.accessibility_preferences or {},
    )


def _collection_response(
    session: Session, user_id: UUID, row: SavedCollection
) -> CollectionResponse:
    share = session.get(CollectionShare, (row.id, user_id))
    is_owner = row.owner_user_id == user_id
    shares = data.collection_shares(session, row.id) if is_owner else []
    return CollectionResponse(
        id=row.id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        description=row.description,
        can_edit=is_owner or bool(share and share.can_edit),
        shared_with_user_ids=[item.shared_with_user_id for item in shares],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _image_type(contents: bytes) -> tuple[str | None, str]:
    if contents.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if contents.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if len(contents) >= 12 and contents[:4] == b"RIFF" and contents[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None, ""


def _document_type(contents: bytes) -> tuple[str | None, str]:
    image = _image_type(contents)
    if image[0]:
        return image
    if contents.startswith(b"%PDF-"):
        return "application/pdf", ".pdf"
    return None, ""


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _read_limited(request: Request, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > maximum:
            raise ApiError(
                413, "upload_too_large", "The uploaded file is larger than the allowed size."
            )
        chunks.append(chunk)
    return b"".join(chunks)
