from fastapi import APIRouter

from .v1 import auth, admin, health

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, prefix="/v1", tags=["health"])
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/v1/admin", tags=["admin"])