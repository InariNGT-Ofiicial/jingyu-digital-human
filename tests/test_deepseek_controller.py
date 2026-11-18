import json
import os
import unittest
from unittest.mock import patch

import deepseek_controller as cloud

try:
    from aiohttp import ClientSession, web
    from aiohttp.test_utils import TestClient, TestServer
except ImportError:
    ClientSession = None


class SettingsTests(unittest.TestCase):
    def test_explicit_cloud_requires_a_key_and_local_is_selectable(self):
        with patch.dict(os.environ, {"JINGYU_CONTROLLER": "deepseek", "DEEPSEEK_API_KEY": ""}):
            self.assertEqual(cloud.provider(), "deepseek")
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                cloud.DeepSeekController()
        with patch.dict(os.environ, {"JINGYU_CONTROLLER": "local", "DEEPSEEK_API_KEY": "fixture"}):
            self.assertEqual(cloud.provider(), "local")


@unittest.skipUnless(ClientSession, "安装 requirements-call.txt 中的 aiohttp 以运行 WebSocket 集成测试")
class PhoneProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import server

        self.requests = []
        self.spoken = []
        self.queue = []
        os_env = patch.dict(os.environ, {"DEEPSEEK_API_KEY": "fixture", "CALL_FAST_A3": "1"})
        os_env.start()
        self.addCleanup(os_env.stop)

        async def completion(req):
            self.assertEqual(req.headers["Authorization"], "Bearer fixture")
            self.requests.append(await req.json())
            status, result = self.queue.pop(0)
            if status != 200:
                return web.Response(status=status, text="private-error-detail")
            content = result if isinstance(result, str) else json.dumps(result)
            return web.json_response({"choices": [{"finish_reason": "stop", "message": {"content": content}}]})

        async def voice(req):
            self.spoken.append((await req.json())["text"])
            return web.Response(body=bytes(4800))

        services = web.Application()
        services.router.add_post("/chat/completions", completion)
        services.router.add_post("/speak", voice)
        backend = TestServer(services)
        await backend.start_server()
        self.addAsyncCleanup(backend.close)
        for module, attr, url in [(cloud, "ENDPOINT", "/chat/completions"), (server, "WORKER", "")]:
            change = patch.object(module, attr, str(backend.make_url(url)).rstrip("/"))
            change.start()
            self.addCleanup(change.stop)
        session = ClientSession()
        self.addAsyncCleanup(session.close)
        app = web.Application()
        app.update(http=session, operator=[None], models=None, controller=cloud.DeepSeekController())
        app.router.add_get("/ws", server.socket)
        client = TestClient(TestServer(app))
        await client.start_server()
        self.addAsyncCleanup(client.close)
        self.ws = await client.ws_connect("/ws")
        self.addAsyncCleanup(self.ws.close)

    async def turn(self, number, text):
        await self.ws.send_json({"type": "turn", "id": number, "text": text, "phone": True, "segmentedAudio": True})
        events = []
        while True:
            event = await self.ws.receive_json(timeout=4)
            self.assertEqual(event["id"], number)
            events.append(event)
            if event["type"] in {"end", "error", "cached"}:
                return events

    async def test_two_open_questions_history_and_gesture(self):
        questions = ["窗边的小猫一直背光，我应该挪到哪里？", "如果这扇窗朝西呢？"]
        reply = "你可以站到窗户旁边，让光从侧面照过来。"
        self.queue.extend([(200, {"reply": reply, "gesture": "think"}),
                           (200, {"reply": "西晒时拉一层薄帘，光会柔和一些。", "gesture": "unknown"})])
        first = await self.turn(1, questions[0])
        self.assertEqual([e["gesture"] for e in first if e["type"] == "gesture"], ["think"])
        self.assertIn("voice_part", [e["type"] for e in first])
        self.assertEqual("".join(self.spoken), reply)
        await self.ws.send_json({"type": "played", "id": 1})
        second = await self.turn(2, questions[1])
        self.assertEqual(second[-1]["type"], "end")
        self.assertNotIn("gesture", [e["type"] for e in second])
        messages = self.requests[1]["messages"]
        self.assertEqual([m["role"] for m in messages[1:]], ["user", "assistant", "user"])
        self.assertEqual([messages[1]["content"], messages[3]["content"]], questions)
        self.assertEqual(json.loads(messages[2]["content"]), {"reply": reply, "gesture": "none"})
        self.assertEqual(self.requests[0]["response_format"], {"type": "json_object"})

    async def test_blank_json_response_retries_once_before_speech(self):
        reply = "是在一九〇四年提出的。"
        self.queue.extend([(200, " " * 15), (200, {"reply": reply, "gesture": "none"})])
        recovered = await self.turn(1, "那它是哪一年提出的？请用一句话告诉我。")
        self.assertEqual(recovered[-1]["type"], "end")
        self.assertEqual(len(self.requests), 2)
        self.assertEqual("".join(self.spoken), reply)
        self.queue.extend([(200, " " * 17), (200, " " * 15)])
        failed = await self.turn(2, "你还记得具体是哪个月份吗？")
        self.assertEqual(failed[-1]["type"], "error")
        self.assertEqual(len(self.requests), 4)
        self.assertEqual("".join(self.spoken), reply)

    async def test_cached_turn_and_cloud_errors(self):
        events = await self.turn(1, "挥挥手")
        self.assertEqual(events[-1]["type"], "cached")
        self.assertFalse(self.requests)
        self.queue.extend([(401, None), (200, {"reply": "  "})])
        rejected = await self.turn(2, "给我讲讲开烘焙店怎么选烤箱")
        self.assertIn("HTTP 401", rejected[-1]["message"])
        self.assertNotIn("private-error-detail", rejected[-1]["message"])
        empty = await self.turn(3, "现在有哪些办法改善采光？")
        self.assertIn("不完整", empty[-1]["message"])
        self.assertFalse(self.spoken)
