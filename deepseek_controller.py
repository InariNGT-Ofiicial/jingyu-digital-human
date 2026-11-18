"""One confirmed turn produces speech text and an optional cast gesture."""
import asyncio
import json
import os

from phone_context import phone_messages

ENDPOINT = "https://api.deepseek.com/chat/completions"
GESTURES = {
    "none": "让动作导演自然选择",
    "acknowledge": "轻轻点头",
    "read-request": "低头看消息",
    "wave": "挥手",
    "listen": "倾听",
    "think": "托腮思考",
    "smile": "浅笑",
}


def provider():
    name = os.environ.get("JINGYU_CONTROLLER") or (
        "deepseek" if os.environ.get("DEEPSEEK_API_KEY", "").strip() else "local"
    )
    if name not in {"deepseek", "local"}:
        raise ValueError("JINGYU_CONTROLLER 应填写 deepseek 或 local。")
    return name


class DeepSeekController:
    def __init__(self):
        self.key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not self.key:
            raise ValueError("DeepSeek 中控缺少 DEEPSEEK_API_KEY，请在运行 server.py 的服务端设置。")
        self.model = os.environ.get("JINGYU_DEEPSEEK_MODEL") or "deepseek-flash"

    async def decide(self, http, text, history):
        import aiohttp

        messages = phone_messages(text, history)
        # The API sees past assistant messages as examples of the required output.
        # Keep the spoken prefix (including after interruption) inside the same schema.
        for message in messages:
            if message["role"] == "assistant":
                message["content"] = json.dumps(
                    {"reply": message["content"], "gesture": "none"}, ensure_ascii=False
                )
        messages[0]["content"] += (
            '\n只输出 JSON 对象，例如 {"reply":"可以先把相机挪到窗边。","gesture":"acknowledge"}。'
            "reply 是可以直接朗读的回答。gesture 最多选一个与当轮话意自然贴合的动作，平常选 none。可选动作："
            + "、".join(f"{k}（{v}）" for k, v in GESTURES.items())
        )
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "max_tokens": 640,
            "stream": False,
        }
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 12
            for attempt in range(2):
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise asyncio.TimeoutError()
                async with http.post(
                    ENDPOINT, json=payload, headers={"Authorization": f"Bearer {self.key}"},
                    timeout=aiohttp.ClientTimeout(total=remaining, ceil_threshold=float("inf")), allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"DeepSeek 中控请求失败（HTTP {response.status}），请检查服务端密钥、额度和模型配置。")
                    data = await response.json()
                choice = data["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise ValueError("incomplete")
                content = choice["message"]["content"]
                if attempt == 0 and isinstance(content, str) and not content.strip():
                    messages[0]["content"] += '\n请务必在 JSON 的 "reply" 字段里写回答，动作不确定时填 "none"。'
                    continue
                break
            result = json.loads(content)
            reply = result["reply"]
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("empty")
            gesture = result.get("gesture")
            if not isinstance(gesture, str) or gesture == "none" or gesture not in GESTURES:
                gesture = None
            return reply.strip(), gesture
        except asyncio.TimeoutError:
            raise RuntimeError("DeepSeek 中控 12 秒内未完成回答，可以重新提问。") from None
        except aiohttp.ClientConnectionError:
            raise RuntimeError("无法连接 DeepSeek 中控，请检查服务端网络。") from None
        except (ValueError, TypeError, IndexError, KeyError, aiohttp.ContentTypeError):
            raise RuntimeError("DeepSeek 中控返回的回答不完整，可以重新提问。") from None
