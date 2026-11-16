from fastapi import APIRouter

from app.config import get_settings
from app.schemas import ConfigResponse

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def config() -> ConfigResponse:
    settings = get_settings()
    return ConfigResponse(
        max_file_mb=settings.max_file_mb,
        name_match_threshold=settings.name_match_threshold,
        name_review_threshold=settings.name_review_threshold,
        amount_tolerance=settings.amount_tolerance,
    )
