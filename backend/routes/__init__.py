"""Route exports for API registration."""

from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.claims import router as claims_router
from routes.payouts import router as payouts_router
from routes.premium import router as premium_router
from routes.registration import router as registration_router
from routes.triggers import router as triggers_router

__all__ = [
    "auth_router",
    "registration_router",
    "premium_router",
    "claims_router",
    "triggers_router",
    "admin_router",
    "payouts_router",
]
