from fastapi import APIRouter

from app.config import get_settings
from app.core.runtime_status import health_payload, liveness_payload, readiness_payload

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str | bool]:
    return health_payload(get_settings())


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return liveness_payload()


@router.get("/health/ready")
async def health_ready() -> dict[str, object]:
    return readiness_payload(get_settings())
