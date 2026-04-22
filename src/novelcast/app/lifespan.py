from contextlib import asynccontextmanager
from fastapi import FastAPI

from novelcast.core.context import AppContext
from novelcast.core.config import AppConfig

from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()
    ctx = AppContext()
    user_service = UserService(ctx.qm)
    auth_service = AuthService(ctx.qm)

    app.state.ctx = ctx
    app.state.db = ctx.db
    app.state.qm = ctx.qm

    app.state.users = user_service
    app.state.auth = auth_service
    app.state.config = config

    print("\n--- App Config ---")
    for key, value in config.model_dump().items():
        print(f"{key:15} = {value}")
    print("------------------\n")

    yield

    ctx.db.close()