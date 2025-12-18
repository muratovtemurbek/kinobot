from aiogram import Router

from .user import router as user_router
from .admin import router as admin_router
from .payment import router as payment_router

router = Router()
# Admin routeri birinchi - state handlerlar to'g'ri ishlashi uchun
router.include_router(admin_router)
router.include_router(payment_router)
router.include_router(user_router)
