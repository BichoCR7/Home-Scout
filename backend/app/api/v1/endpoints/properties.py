"""Published public property reads and owner-only draft operations."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db, get_optional_principal, get_settings
from app.core.config import Settings
from app.core.errors import ApiError
from app.schemas.properties import (
    AvailabilityUpdate,
    ListingAgentAssignment,
    PropertyCreateRequest,
    PropertyListResponse,
    PropertyMediaResponse,
    PropertyPatchRequest,
    PropertyResponse,
)
from app.services.authentication import AuthenticatedPrincipal
from app.services.media_storage import LocalMediaStorage
from app.services.properties import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])
service = PropertyService()


@router.get("", response_model=PropertyListResponse, summary="Search published properties")
def list_properties(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    county_id: UUID | None = None,
    town_id: UUID | None = None,
    neighbourhood_id: UUID | None = None,
    property_type: Literal["apartment", "house", "maisonette", "villa", "townhouse"] | None = None,
    unit_type: Literal[
        "bedsitter",
        "studio",
        "one_bedroom",
        "two_bedroom",
        "three_bedroom",
        "four_bedroom",
        "five_plus_bedrooms",
    ]
    | None = None,
    bedrooms: Annotated[int | None, Query(ge=0, le=50)] = None,
    bedrooms_min: Annotated[int | None, Query(ge=0, le=50)] = None,
    furnishing: Literal["furnished", "unfurnished", "semi_furnished"] | None = None,
    verified_only: bool = False,
    rent_min: Annotated[int | None, Query(ge=1)] = None,
    rent_max: Annotated[int | None, Query(ge=1)] = None,
    query: Annotated[str | None, Query(max_length=120)] = None,
    amenities: Annotated[list[str] | None, Query(max_length=20)] = None,
    sort_by: Literal["newest", "rent_low", "rent_high", "bedrooms"] = "newest",
    south: Annotated[float | None, Query(ge=-90, le=90)] = None,
    west: Annotated[float | None, Query(ge=-180, le=180)] = None,
    north: Annotated[float | None, Query(ge=-90, le=90)] = None,
    east: Annotated[float | None, Query(ge=-180, le=180)] = None,
    include_demo: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> PropertyListResponse:
    bounds = (south, west, north, east)
    if any(value is not None for value in bounds) and not all(
        value is not None for value in bounds
    ):
        raise ApiError(
            422,
            "incomplete_map_bounds",
            "All four map bounds must be supplied together.",
        )
    if rent_min is not None and rent_max is not None and rent_min > rent_max:
        raise ApiError(422, "invalid_rent_range", "Minimum rent cannot exceed maximum rent.")
    if bedrooms is not None and bedrooms_min is not None:
        raise ApiError(
            422,
            "ambiguous_bedroom_filter",
            "Choose an exact bedroom count or a minimum count.",
        )
    if south is not None and north is not None and south >= north:
        raise ApiError(422, "invalid_map_bounds", "South latitude must be below north latitude.")
    if west is not None and east is not None and west == east:
        raise ApiError(422, "invalid_map_bounds", "Map bounds must include a longitude range.")
    clean_amenities = list(
        dict.fromkeys(value.strip() for value in (amenities or []) if value.strip())
    )
    if any(len(value) > 80 for value in clean_amenities):
        raise ApiError(422, "invalid_amenity", "Amenity names must be 80 characters or fewer.")
    return service.list_public(
        session,
        county_id=county_id,
        town_id=town_id,
        neighbourhood_id=neighbourhood_id,
        property_type=property_type,
        unit_type=unit_type,
        bedrooms=bedrooms,
        bedrooms_min=bedrooms_min,
        furnishing=furnishing,
        verified_only=verified_only,
        rent_min=rent_min,
        rent_max=rent_max,
        query=query,
        amenities=clean_amenities,
        sort_by=sort_by,
        south=south,
        west=west,
        north=north,
        east=east,
        include_demo=include_demo and settings.environment in {"development", "test"},
        limit=limit,
        offset=offset,
    )


@router.get("/mine", response_model=list[PropertyResponse], summary="List my draft properties")
def list_my_properties(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> list[PropertyResponse]:
    return service.list_owned(session, user_id=principal.user_id)


@router.get("/{property_id}", response_model=PropertyResponse, summary="Read a published property")
def get_property(
    property_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    include_demo: bool = False,
) -> PropertyResponse:
    return service.get_public(
        session,
        property_id,
        include_demo=include_demo and settings.environment in {"development", "test"},
    )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an owner-scoped draft property",
)
def create_property(
    body: PropertyCreateRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.create_draft(
        session,
        user_id=principal.user_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Update an owner-scoped draft property",
)
def update_property(
    property_id: UUID,
    body: PropertyPatchRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.update_draft(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/{property_id}/preview",
    response_model=PropertyResponse,
    summary="Preview a listing available to its owner or assigned manager",
)
def preview_property(
    property_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.get_preview(session, user_id=principal.user_id, property_id=property_id)


@router.post(
    "/{property_id}/assignments",
    response_model=PropertyResponse,
    summary="Assign an eligible agent or property manager",
)
def assign_listing_party(
    property_id: UUID,
    body: ListingAgentAssignment,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.assign_listing_party(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        assignment=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/{property_id}/availability", response_model=PropertyResponse)
def update_availability(
    property_id: UUID,
    body: AvailabilityUpdate,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.set_availability(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        request=body,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/{property_id}/publish", response_model=PropertyResponse)
def publish_property(
    property_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.publish(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/{property_id}/archive", response_model=PropertyResponse)
def archive_property(
    property_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> PropertyResponse:
    return service.archive(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_property(
    property_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.delete_draft(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        storage=LocalMediaStorage(request.app.state.settings.media_storage_dir),
        request_id=getattr(request.state, "request_id", None),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{property_id}/media",
    response_model=PropertyMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a listing image",
)
async def upload_property_image(
    property_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
    alt_text: Annotated[str | None, Query(max_length=300)] = None,
) -> PropertyMediaResponse:
    service.assert_can_edit_listing(session, user_id=principal.user_id, property_id=property_id)
    mime_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ApiError(415, "unsupported_image", "Upload a JPEG, PNG, or WebP image.")
    maximum = request.app.state.settings.media_max_image_bytes
    contents = bytearray()
    async for chunk in request.stream():
        if len(contents) + len(chunk) > maximum:
            raise ApiError(413, "image_too_large", "The image exceeds the configured upload limit.")
        contents.extend(chunk)
    raw = bytes(contents)
    signatures = {
        "image/jpeg": raw.startswith(b"\xff\xd8\xff"),
        "image/png": raw.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
    }
    if not raw or not signatures[mime_type]:
        raise ApiError(
            415, "invalid_image_content", "The image content does not match its file type."
        )
    storage = LocalMediaStorage(request.app.state.settings.media_storage_dir)
    return service.upload_image(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        contents=raw,
        mime_type=mime_type,
        alt_text=alt_text.strip() if alt_text else None,
        storage=storage,
        request_id=getattr(request.state, "request_id", None),
    )


@router.delete("/{property_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_image(
    property_id: UUID,
    media_id: UUID,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    service.delete_media(
        session,
        user_id=principal.user_id,
        property_id=property_id,
        media_id=media_id,
        storage=LocalMediaStorage(request.app.state.settings.media_storage_dir),
        request_id=getattr(request.state, "request_id", None),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{property_id}/similar", response_model=PropertyListResponse)
def similar_properties(
    property_id: UUID,
    session: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> PropertyListResponse:
    from app.services.marketplace import MarketplaceService

    return MarketplaceService().similar(session, property_id=property_id, limit=limit)


@router.get("/media/{media_id}")
def read_property_image(
    media_id: UUID,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    principal: Annotated[AuthenticatedPrincipal | None, Depends(get_optional_principal)],
):
    from app.models.property import Property, PropertyMedia

    media = session.get(PropertyMedia, media_id)
    property_ = session.get(Property, media.property_id) if media else None
    if media is None or property_ is None or media.storage_key is None or media.mime_type is None:
        raise ApiError(404, "media_not_found", "The requested listing image was not found.")
    public = (
        not property_.is_demo
        and property_.listing_status == "published"
        and property_.availability_status == "available"
    )
    if not public:
        if principal is None:
            raise ApiError(404, "media_not_found", "The requested listing image was not found.")
        service.get_preview(session, user_id=principal.user_id, property_id=property_.id)
    path = LocalMediaStorage(request.app.state.settings.media_storage_dir).get(media.storage_key)
    if path is None:
        raise ApiError(404, "media_not_found", "The requested listing image was not found.")
    cache_control = "public, max-age=3600" if public else "private, no-store"
    return FileResponse(
        path,
        media_type=media.mime_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": cache_control},
    )
