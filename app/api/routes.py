from fastapi import APIRouter

from app.config import get_settings
from app.core.runtime_status import health_payload

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str | bool]:
    return health_payload(get_settings())
