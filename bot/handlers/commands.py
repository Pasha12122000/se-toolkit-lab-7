from config import Settings


WELCOME_TEXT = (
    "Welcome to the LMS bot.\n"
    "Use /help to see the available commands."
)

HELP_TEXT = (
    "Available commands:\n"
    "/start - welcome message\n"
    "/help - show available commands\n"
    "/health - check backend connectivity\n"
    "/labs - list available labs\n"
    "/scores <lab> - show pass rates for a lab"
)


def handle_start(_: Settings) -> str:
    return WELCOME_TEXT


def handle_help(_: Settings) -> str:
    return HELP_TEXT


def handle_health(settings: Settings) -> str:
    return (
        "Health check is scaffolded. "
        f"Backend is configured at {settings.lms_api_base_url}."
    )


def handle_labs(_: Settings) -> str:
    return "Labs list is not implemented yet."


def handle_scores(_: Settings, lab: str | None) -> str:
    if not lab:
        return "Usage: /scores <lab>"

    return f"Scores for {lab} are not implemented yet."
