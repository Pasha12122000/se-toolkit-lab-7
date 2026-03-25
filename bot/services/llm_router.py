import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx

from config import Settings
from services.lms_api import BackendError, LmsApiClient


LLM_TIMEOUT_SECONDS = 60.0
MAX_TOOL_ROUNDS = 20


@dataclass
class LlmError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List labs and tasks from the LMS backend.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get enrolled students and their groups.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get score distribution buckets for a lab like lab-04.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get group performance statistics for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get the top learners for a lab, or top learners overall if the user asks for a lab and limit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of learners to return.",
                        "default": 5,
                    },
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate statistics for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as lab-04.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Refresh backend data from the autochecker when the user explicitly asks to sync or refresh data.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


SYSTEM_PROMPT = """
You are an LMS bot assistant. For natural-language questions, decide whether you need backend tools.

Rules:
- Use the provided tools whenever backend data is needed.
- You may call multiple tools in sequence before answering.
- Prefer batching independent tool calls in one assistant turn when comparing multiple labs.
- Do not stop with a progress update like "let me check" or "I will inspect".
- Only produce a final answer after you have enough data to answer the user's question directly.
- For comparison questions such as "lowest", "highest", "best", "worst", or "compare", collect all relevant tool results before answering.
- If the user asks which lab is lowest or highest, inspect the available labs first and then compare the relevant analytics across those labs.
- After you have enough tool results for a comparison, stop calling tools and give the final answer.
- When comparing labs, use `get_items` to identify the available lab IDs, then call `get_pass_rates` for every lab in the same tool-calling turn if possible.
- For this course, the relevant lab identifiers are usually `lab-01` through `lab-07`; after checking available labs, compare them all instead of checking just one or two.
- If the user is greeting you or sends gibberish, answer helpfully without tools.
- If the user is ambiguous, ask a short clarifying question.
- When you have tool results, summarize them clearly and include specific numbers when available.
- Do not invent backend data.
""".strip()


class LlmRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api = LmsApiClient(settings)

    async def route(self, user_message: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            assistant_message = await self._chat(messages)
            tool_calls = assistant_message.get("tool_calls", [])
            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                )
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = self._parse_tool_arguments(
                        tool_call["function"].get("arguments", "{}")
                    )
                    print(
                        f"[tool] LLM called: {tool_name}({json.dumps(tool_args, ensure_ascii=True)})",
                        file=sys.stderr,
                    )
                    result = await self._execute_tool(tool_name, tool_args)
                    print(
                        f"[tool] Result: {self._describe_result(result)}",
                        file=sys.stderr,
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                print(
                    f"[summary] Feeding {len(tool_calls)} tool result(s) back to LLM",
                    file=sys.stderr,
                )
                continue

            content = (assistant_message.get("content") or "").strip()
            if content:
                return content

        raise LlmError("LLM error: tool loop exceeded the maximum number of steps.")

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if not self._settings.llm_api_base_url or not self._settings.llm_api_key:
            raise LlmError("LLM error: LLM API credentials are missing.")

        url = f"{self._settings.llm_api_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self._settings.llm_api_model or "coder-model",
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise LlmError(f"LLM error: HTTP {status_code}.") from exc
        except httpx.RequestError as exc:
            raise LlmError(f"LLM error: {exc}.") from exc

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise LlmError("LLM error: empty response from the model.")

        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise LlmError("LLM error: malformed response from the model.")
        return message

    async def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        try:
            if tool_name == "get_items":
                return await self._api.get_items()
            if tool_name == "get_learners":
                return await self._api.get_learners()
            if tool_name == "get_scores":
                return await self._api.get_scores(str(tool_args["lab"]).lower())
            if tool_name == "get_pass_rates":
                return await self._api.get_pass_rates(str(tool_args["lab"]).lower())
            if tool_name == "get_timeline":
                return await self._api.get_timeline(str(tool_args["lab"]).lower())
            if tool_name == "get_groups":
                return await self._api.get_groups(str(tool_args["lab"]).lower())
            if tool_name == "get_top_learners":
                limit = int(tool_args.get("limit", 5))
                return await self._api.get_top_learners(
                    str(tool_args["lab"]).lower(),
                    limit=limit,
                )
            if tool_name == "get_completion_rate":
                return await self._api.get_completion_rate(str(tool_args["lab"]).lower())
            if tool_name == "trigger_sync":
                return await self._api.trigger_sync()
        except KeyError as exc:
            raise LlmError(
                f"LLM error: tool {tool_name} is missing required argument {exc.args[0]}."
            ) from exc
        except BackendError as exc:
            return {"error": str(exc)}

        raise LlmError(f"LLM error: unknown tool {tool_name}.")

    def _parse_tool_arguments(self, raw_arguments: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            raise LlmError("LLM error: tool arguments were not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise LlmError("LLM error: tool arguments must decode to an object.")
        return parsed

    def _describe_result(self, result: Any) -> str:
        if isinstance(result, list):
            return f"{len(result)} item(s)"
        if isinstance(result, dict):
            return f"object with keys: {', '.join(sorted(result.keys()))}"
        return type(result).__name__
