"""Raah Saathi FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import Base, engine
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.claims import router as claims_router
from routes.payouts import router as payouts_router
from routes.premium import router as premium_router
from routes.registration import router as registration_router
from routes.triggers import router as triggers_router
from scheduler import start_scheduler, stop_scheduler

app = FastAPI(title="Raah Saathi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/health", status_code=status.HTTP_200_OK)
def health() -> dict:
    return {"status": "ok", "service": "raah-saathi-api"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not Found"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal Server Error"})


app.include_router(registration_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(premium_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")
app.include_router(triggers_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(payouts_router, prefix="/api/v1")

# Backward-compatible auth routes for clients still calling /auth/* directly.
app.include_router(auth_router)
