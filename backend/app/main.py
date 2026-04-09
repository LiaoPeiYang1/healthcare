from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models import Base
from app.routers import auth, file, history, translate
from app.services.auth_service import auth_service
from app.services.terminology_service import terminology_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await auth_service.ensure_seed_user(session)
        await terminology_service.ensure_seed_terms(session)

    yield


app = FastAPI(title=settings.app_name, version='0.1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(file.router, prefix=settings.api_prefix)
app.include_router(history.router, prefix=settings.api_prefix)
app.include_router(translate.router, prefix=settings.api_prefix)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
