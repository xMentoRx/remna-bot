from aiogram import Router
from handlers.start_onboarding import router as onboarding_router
from handlers.node_handlers import router as node_router
from handlers.user_handlers import router as user_router

def setup_routers() -> Router:
    """Combines all modular feature routers into a main application router."""
    main_router = Router(name="main_router")
    main_router.include_router(onboarding_router)
    main_router.include_router(node_router)
    main_router.include_router(user_router)
    return main_router
