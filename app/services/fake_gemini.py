"""
Fake Gemini test double for testing and CI without external API dependencies.
Refused when ENV=production.
"""
from typing import Any, Dict, List, Optional


class FakeFunctionCall:
    def __init__(self, name: str, args: Optional[Dict[str, Any]] = None):
        self.name = name
        self.args = args or {}


class FakeResponse:
    def __init__(self, text: Optional[str] = None, function_calls: Optional[List[FakeFunctionCall]] = None):
        self.text = text or ""
        self.function_calls = function_calls or []


class FakeChat:
    def __init__(self, model: str, history: Optional[List[Any]] = None, config: Optional[Any] = None):
        self.model = model
        self.history = list(history or [])
        self.config = config

    def send_message(self, message_or_parts: Any) -> FakeResponse:
        # If passed a list of function responses from tool execution
        if isinstance(message_or_parts, list):
            results = []
            for item in message_or_parts:
                fn_res = getattr(item, "function_response", None)
                if fn_res:
                    name = getattr(fn_res, "name", "tool")
                    resp = getattr(fn_res, "response", {})
                    snippet = str(resp.get("result", ""))[:200]
                    results.append(f"{name}: {snippet}")
            return FakeResponse(
                text=f"[Fake Model] Tool execution finished. Observed results: {'; '.join(results)}"
            )

        text_msg = str(message_or_parts)

        # Trigger simulated quota error for testing error handling
        if "trigger_quota_error" in text_msg:
            raise Exception("RESOURCE_EXHAUSTED 429 quota exceeded for model")

        # Trigger scripted tool execution
        # Format: call_tool:<tool_name> or call_tool:<tool_name>:<k1>=<v1>,<k2>=<v2>
        if text_msg.startswith("call_tool:"):
            body = text_msg[len("call_tool:"):].strip()
            if ":" in body:
                tool_name, raw_args = body.split(":", 1)
                args = {}
                for pair in raw_args.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        args[k.strip()] = v.strip()
            else:
                tool_name = body
                args = {}

            return FakeResponse(
                text="",
                function_calls=[FakeFunctionCall(name=tool_name, args=args)],
            )

        # Standard simulated response
        return FakeResponse(
            text=f"[Fake Gemini Double - Model: {self.model}] Received message: {text_msg}"
        )


class FakeChats:
    def create(self, model: str, history: Optional[List[Any]] = None, config: Optional[Any] = None) -> FakeChat:
        return FakeChat(model=model, history=history, config=config)


class FakeModel:
    def __init__(self, name: str):
        self.name = name


class FakeModels:
    def list(self):
        return [
            FakeModel("models/gemini-2.5-flash"),
            FakeModel("models/gemini-2.5-flash-lite"),
        ]


class FakeGenaiClient:
    def __init__(self):
        self.chats = FakeChats()
        self.models = FakeModels()

