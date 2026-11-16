import importlib
import os
import unittest
from unittest import mock


def load_config(env):
    keys = [k for k in os.environ if k.startswith(("GROQ_", "TELEGRAM_", "ADMIN_"))]
    clean = {k: v for k, v in os.environ.items() if k not in keys}
    clean.update(env)
    with mock.patch.dict(os.environ, clean, clear=True):
        import trading_bot.config as config
        with mock.patch("dotenv.load_dotenv", lambda *a, **k: False):
            return importlib.reload(config)


class ConfigTests(unittest.TestCase):
    def test_seven_keys_loaded_in_order(self):
        env = {f"GROQ_API_KEY_{i}": f"gsk_{i}" for i in range(1, 8)}
        cfg = load_config(env)
        self.assertEqual(cfg.GROQ_API_KEYS, [f"gsk_{i}" for i in range(1, 8)])
        self.assertTrue(cfg.GROQ_ENABLED)

    def test_default_model_is_llama_versatile(self):
        self.assertEqual(load_config({}).GROQ_MODEL, "llama-3.3-70b-versatile")

    def test_placeholders_are_ignored(self):
        cfg = load_config({"GROQ_API_KEY_1": "clave_groq_1", "TELEGRAM_BOT_TOKEN": "TU_TOKEN_TELEGRAM",
                           "TELEGRAM_CHAT_ID": "TU_CHAT_ID"})
        self.assertEqual(cfg.GROQ_API_KEYS, [])
        self.assertEqual(cfg.TOKEN, "")
        self.assertEqual(cfg.ADMIN_CHAT_ID, "")

    def test_legacy_variables_still_work(self):
        cfg = load_config({"GROQ_API_KEY": "gsk_old", "ADMIN_CHAT_ID": "123"})
        self.assertEqual(cfg.GROQ_API_KEYS, ["gsk_old"])
        self.assertEqual(cfg.ADMIN_CHAT_ID, "123")

    def test_telegram_chat_id_has_priority(self):
        cfg = load_config({"TELEGRAM_CHAT_ID": "999", "ADMIN_CHAT_ID": "123"})
        self.assertEqual(cfg.ADMIN_CHAT_ID, "999")

    def test_duplicates_removed(self):
        cfg = load_config({"GROQ_API_KEY_1": "a", "GROQ_API_KEY_2": "a", "GROQ_API_KEY": "a"})
        self.assertEqual(cfg.GROQ_API_KEYS, ["a"])

    def test_timeframes_include_macro_and_operative(self):
        cfg = load_config({})
        for tf in ("1d", "4h", "1h", "15m"):
            self.assertIn(tf, cfg.TIMEFRAMES)
        self.assertEqual(cfg.MACRO_TIMEFRAMES, ("1d", "4h"))
        self.assertEqual(cfg.OPERATIVE_TIMEFRAMES, ("1h", "15m"))

    def test_resolve_asset_aliases(self):
        cfg = load_config({})
        self.assertEqual(cfg.resolve_asset("BTCUSDT"), "BTC/USD")
        self.assertEqual(cfg.resolve_asset("ethusdt"), "ETH/USD")
        self.assertEqual(cfg.resolve_asset("EURUSD"), "EUR/USD")
        self.assertEqual(cfg.resolve_asset("eur/usd"), "EUR/USD")
        self.assertEqual(cfg.resolve_asset("AAPL"), "AAPL")
        self.assertEqual(cfg.resolve_asset("EURUSD=X"), "EUR/USD")
        self.assertIsNone(cfg.resolve_asset("NOEXISTE"))
        self.assertIsNone(cfg.resolve_asset(""))


if __name__ == "__main__":
    unittest.main()
