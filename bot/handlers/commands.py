from collections.abc import Iterable

from config import Settings
from services import BackendError, LmsApiClient


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


def _extract_labs(items: Iterable[dict]) -> list[dict]:
    labs = [item for item in items if item.get("type") == "lab"]
    return sorted(labs, key=lambda item: str(item.get("title", "")))


async def handle_health(settings: Settings) -> str:
    client = LmsApiClient(settings)
    try:
        items = await client.get_items()
    except BackendError as exc:
        return str(exc)

    return f"Backend is healthy. {len(items)} items available."


async def handle_labs(settings: Settings) -> str:
    client = LmsApiClient(settings)
    try:
        items = await client.get_items()
    except BackendError as exc:
        return str(exc)

    labs = _extract_labs(items)
    if not labs:
        return "No labs found in the backend data."

    lines = ["Available labs:"]
    for lab in labs:
        lines.append(f"- {lab['title']}")
    return "\n".join(lines)


async def handle_scores(settings: Settings, lab: str | None) -> str:
    if not lab:
        return "Usage: /scores <lab>"

    normalized_lab = lab.lower()
    client = LmsApiClient(settings)
    try:
        pass_rates = await client.get_pass_rates(normalized_lab)
    except BackendError as exc:
        return str(exc)

    if not pass_rates:
        return f"No score data found for {normalized_lab}."

    lines = [f"Pass rates for {normalized_lab}:"]
    for entry in pass_rates:
        task = entry.get("task", "Unknown task")
        avg_score = entry.get("avg_score", 0.0)
        attempts = entry.get("attempts", 0)
        lines.append(f"- {task}: {avg_score}% ({attempts} attempts)")
    return "\n".join(lines)
