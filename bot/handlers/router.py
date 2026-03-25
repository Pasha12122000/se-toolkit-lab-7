from config import Settings
from handlers.common import UNKNOWN_COMMAND_TEXT
from handlers.commands import (
    handle_health,
    handle_help,
    handle_labs,
    handle_scores,
    handle_start,
)


async def dispatch_message(message_text: str, settings: Settings) -> str:
    text = message_text.strip()
    if not text:
        return "Please enter a command. Use /help to see the available commands."

    parts = text.split()
    command = parts[0].lower()

    if command == "/start":
        return handle_start(settings)
    if command == "/help":
        return handle_help(settings)
    if command == "/health":
        return await handle_health(settings)
    if command == "/labs":
        return await handle_labs(settings)
    if command == "/scores":
        lab = parts[1] if len(parts) > 1 else None
        return await handle_scores(settings, lab)

    return UNKNOWN_COMMAND_TEXT
