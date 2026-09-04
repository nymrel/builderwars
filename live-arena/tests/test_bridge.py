import importlib.util
import http.client
import json
from pathlib import Path
import threading
import unittest

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).parents[1] / "bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Backend:
    calls = 0
    def complete(self, prompt):
        self.calls += 1
        return '{"move":"e2e4","comment":"Center"}'


class Tests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.server = bridge.BridgeServer(("127.0.0.1", 0), bridge.handler_for(self.backend, "synthetic-token", "https://builderwars.example", "test", 1))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def call(self, origin="https://builderwars.example", token="synthetic-token", body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        payload = body or {"schema":"builderwars.move.v1", "legalMoves":["e2e4"], "turn":0, "game":{"name":"Chess"}, "position":"initial"}
        conn.request("POST", "/move", json.dumps(payload), {"Origin":origin,"Authorization":f"Bearer {token}","Content-Type":"application/json"})
        res = conn.getresponse()
        result = res.status, json.loads(res.read())
        conn.close()
        return result

    def test_auth_and_origin_precede_provider(self):
        self.assertEqual(self.call(origin="https://evil.example")[0], 403)
        self.assertEqual(self.call(token="wrong")[0], 401)
        self.assertEqual(self.backend.calls, 0)

    def test_move_and_session_limit(self):
        status, value = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(value["move"], "e2e4")
        self.assertEqual(self.call()[0], 429)
        self.assertEqual(self.backend.calls, 1)

    def test_invalid_body_never_calls_provider(self):
        self.assertEqual(self.call(body={"schema":"builderwars.move.v1","legalMoves":[]})[0], 400)
        self.assertEqual(self.backend.calls, 0)

    def test_move_output_is_bounded_and_legal(self):
        with self.assertRaises(ValueError):
            bridge.parse_move('{"move":"e2e8"}', ["e2e4"])
        self.assertEqual(bridge.parse_move('```json\n{"move":"e2e4"}\n```', ["e2e4"])["move"], "e2e4")


if __name__ == "__main__":
    unittest.main()
