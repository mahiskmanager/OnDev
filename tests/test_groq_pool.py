import unittest
from unittest import mock

from trading_bot import groq_pool
from trading_bot.groq_pool import KeyRotator


class FakeResponse:
    def __init__(self, status, content="ok", headers=None):
        self.status_code = status
        self._content = content
        self.headers = headers or {}
        self.text = f"status {status}"

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class RotatorTests(unittest.TestCase):
    def test_round_robin_over_seven_keys(self):
        pool = KeyRotator([f"k{i}" for i in range(1, 8)])
        order = [pool.next_key()[1] for _ in range(14)]
        self.assertEqual(order[:7], [f"k{i}" for i in range(1, 8)])
        self.assertEqual(order[7:], order[:7])

    def test_blocked_key_is_skipped(self):
        pool = KeyRotator(["a", "b", "c"])
        pool.block(1, 100)
        picked = [pool.next_key()[1] for _ in range(4)]
        self.assertNotIn("b", picked)
        self.assertEqual(pool.available(), 2)

    def test_all_blocked_still_returns_one(self):
        pool = KeyRotator(["a", "b"])
        pool.block(0, 100)
        pool.block(1, 50)
        self.assertEqual(pool.next_key()[1], "b")

    def test_duplicates_and_empty_ignored(self):
        pool = KeyRotator(["a", "", "a", "b"])
        self.assertEqual(pool.size, 2)
        self.assertIsNone(KeyRotator([]).next_key())


class ChatCompletionTests(unittest.TestCase):
    def test_rotates_after_rate_limit(self):
        pool = KeyRotator(["k1", "k2", "k3"])
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(headers["Authorization"])
            return FakeResponse(429 if len(calls) == 1 else 200, '{"x": 1}')

        with mock.patch.object(groq_pool.requests, "post", side_effect=fake_post):
            out = groq_pool.chat_completion({"model": "m"}, pool=pool)
        self.assertEqual(out, '{"x": 1}')
        self.assertEqual(calls, ["Bearer k1", "Bearer k2"])
        self.assertEqual(pool.available(), 2)

    def test_each_request_uses_next_key(self):
        pool = KeyRotator(["k1", "k2", "k3"])
        used = []
        with mock.patch.object(groq_pool.requests, "post",
                               side_effect=lambda url, headers, json, timeout: used.append(headers["Authorization"]) or FakeResponse(200)):
            for _ in range(4):
                groq_pool.chat_completion({}, pool=pool)
        self.assertEqual(used, ["Bearer k1", "Bearer k2", "Bearer k3", "Bearer k1"])

    def test_all_keys_failing_raises(self):
        pool = KeyRotator(["k1", "k2"])
        with mock.patch.object(groq_pool.requests, "post", return_value=FakeResponse(429)):
            with self.assertRaises(RuntimeError):
                groq_pool.chat_completion({}, pool=pool)

    def test_bad_request_does_not_burn_every_key(self):
        pool = KeyRotator(["k1", "k2", "k3"])
        with mock.patch.object(groq_pool.requests, "post", return_value=FakeResponse(400)) as post:
            with self.assertRaises(RuntimeError):
                groq_pool.chat_completion({}, pool=pool)
        self.assertEqual(post.call_count, 1)

    def test_no_keys(self):
        with self.assertRaises(RuntimeError):
            groq_pool.chat_completion({}, pool=KeyRotator([]))


if __name__ == "__main__":
    unittest.main()
