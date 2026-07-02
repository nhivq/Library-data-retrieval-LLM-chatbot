from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_admin_user
from app.database.connection import get_db
from app.services import analytics_service


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/analytics")
def get_analytics(
        admin=Depends(get_current_admin_user),
        conn=Depends(get_db)
):
    try:

        return analytics_service.get_dashboard_analytics(
            conn=conn
        )

    except Exception as e:

        print(e)

        raise HTTPException(
            status_code=400,
            detail="Could not load analytics"
        )
