from typing import Annotated

from animedownloader_nyaa import NyaaClient, NyaaError
from fastapi import APIRouter, Depends, HTTPException, Query

from animedownloader_api.dependencies import (
    get_nyaa_client,
    get_release_discovery_service,
)
from animedownloader_api.release_discovery import ReleaseDiscoveryService
from animedownloader_api.schemas import (
    ParsedReleaseResponse,
    ReleaseDiscoveryItemResponse,
    ReleaseDiscoveryResponse,
    ReleaseResponse,
    ReleaseSearchResponse,
)

router = APIRouter(prefix="/api/releases", tags=["releases"])


@router.get("/search", response_model=ReleaseSearchResponse)
async def search_releases(
    query: Annotated[str, Query(alias="q", min_length=1, max_length=200)],
    client: Annotated[NyaaClient, Depends(get_nyaa_client)],
) -> ReleaseSearchResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(status_code=422, detail="Search query must not be empty")

    try:
        releases = await client.search(normalized_query)
    except NyaaError as exc:
        raise HTTPException(
            status_code=502,
            detail="Nyaa search is temporarily unavailable",
        ) from exc

    return ReleaseSearchResponse(
        query=normalized_query,
        items=[ReleaseResponse.model_validate(release) for release in releases],
    )


ReleaseDiscoveryServiceDependency = Annotated[
    ReleaseDiscoveryService,
    Depends(get_release_discovery_service),
]


@router.get("/discover", response_model=ReleaseDiscoveryResponse)
async def discover_releases(
    title: Annotated[str, Query(min_length=1, max_length=200)],
    service: ReleaseDiscoveryServiceDependency,
    group: Annotated[str | None, Query(max_length=128)] = None,
    episode: Annotated[int | None, Query(ge=1, le=9999)] = None,
    resolution: Annotated[str | None, Query(max_length=32)] = None,
    codec: Annotated[str | None, Query(max_length=32)] = None,
) -> ReleaseDiscoveryResponse:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(status_code=422, detail="Search title must not be empty")

    result = await service.discover(
        title=normalized_title,
        group=group.strip() if group else None,
        episode=episode,
        resolution=resolution.strip() if resolution else None,
        codec=codec.strip() if codec else None,
    )
    return ReleaseDiscoveryResponse(
        queries=list(result.queries),
        failed_queries=list(result.failed_queries),
        warnings=list(result.warnings),
        search_profile_version=result.search_profile_version,
        items=[
            {
                ReleaseDiscoveryItemResponse(
                    release=ReleaseResponse.model_validate(item.release),
                    parsed=ParsedReleaseResponse.from_parsed(item.parsed),
                ),
            }
            for item in result.items
        ],
    )
