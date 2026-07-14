import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.dependencies import get_current_admin_user
from backend.app.database.connection import get_db
from backend.app.services import analytics_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/analytics")
def get_analytics(
        admin=Depends(get_current_admin_user),
        conn=Depends(get_db)
):
    """Return dashboard analytics; access is restricted to admin users."""

    try:

        return analytics_service.get_dashboard_analytics(
            conn=conn
        )

    except Exception as e:

        logger.exception(
            "admin analytics failed",
            extra={"event": "admin_analytics_error", "error": str(e)},
        )

        raise HTTPException(
            status_code=400,
            detail="Could not load analytics"
        )
