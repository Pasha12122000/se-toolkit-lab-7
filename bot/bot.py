import argparse
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import load_settings
from handlers import dispatch_message


async def handle_telegram_message(message: Message) -> None:
    settings = load_settings()
    response_text = await dispatch_message(message.text or "", settings)
    await message.answer(response_text)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.message.register(handle_telegram_message, CommandStart())
    dispatcher.message.register(handle_telegram_message)
    return dispatcher


async def run_telegram_mode() -> None:
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required for Telegram mode.")
    bot = Bot(token=settings.bot_token)
    dispatcher = build_dispatcher()
    await dispatcher.start_polling(bot)


async def run_test_mode(message_text: str) -> int:
    settings = load_settings()
    response_text = await dispatch_message(message_text, settings)
    print(response_text)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LMS Telegram bot")
    parser.add_argument("--test", metavar="MESSAGE", help="Run the bot in CLI test mode")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.test is not None:
        return asyncio.run(run_test_mode(args.test))

    asyncio.run(run_telegram_mode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
