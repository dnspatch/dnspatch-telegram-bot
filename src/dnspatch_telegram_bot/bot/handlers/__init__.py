"""The commands of the bot, one module and one router for each."""

from aiogram import Router

from dnspatch_telegram_bot.bot.handlers import start, status, subscription

router = Router(name="handlers")
router.include_routers(start.router, subscription.router, status.router)
