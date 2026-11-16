import unittest
from html.parser import HTMLParser

from tests.helpers import zigzag_frame
from tests.test_trader import DOWN, UP, frames
from trading_bot.formatting import trader_message
from trading_bot.trader import AMBIGUOUS_PHRASE, evaluate_institutional


class TagChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.errors.append(tag)


def decorate(r, asset="EUR/USD"):
    r.update({"asset": asset, "ticker": "EURUSD=X", "has_15m": True, "age_minutes": 3.0,
              "last_candle_utc": "2026-11-15T10:00:00+00:00"})
    return r


def valid_html(text):
    checker = TagChecker()
    checker.feed(text)
    return not checker.errors and not checker.stack


class MessageTests(unittest.TestCase):
    def test_trade_message_has_all_sections(self):
        for seed in range(1, 40):
            r = decorate(evaluate_institutional(frames(UP, (12, -5), seed), min_confluence=1))
            if r["setup"]:
                break
        text = trader_message(r)
        for marker in ("📊", "🔍", "📰", "📈 <b>Análisis técnico", "⚖️", "🎯", "⏱️", "📈 <b>Rentabilidad", "🧠", "⚠️"):
            self.assertIn(marker, text)
        for word in ("Entrada:", "SL:", "TP1:", "TP2:", "R:R:"):
            self.assertIn(word, text)
        self.assertLessEqual(len(text), 4096)
        self.assertTrue(valid_html(text))

    def test_ambiguous_message_uses_exact_phrase(self):
        f = frames(UP, (12, -5))
        f["4h"] = zigzag_frame(DOWN, start=140, seed=7, noise=0.3)
        r = decorate(evaluate_institutional(f))
        text = trader_message(r)
        self.assertIn(AMBIGUOUS_PHRASE, text)
        self.assertIn("NO TRADE", text)
        self.assertIn("N/A", text)
        self.assertTrue(valid_html(text))

    def test_html_in_dynamic_text_is_escaped(self):
        r = decorate(evaluate_institutional(frames(UP, (12, -5), 1)))
        r["news"] = {**r["news"], "news_summary": "<script>alert(1)</script> & más", "macro_events": "<b>x"}
        r["narrative"] = {"reasoning": "a < b", "macro_context": "<i>", "risk_notice": "&"}
        text = trader_message(r)
        self.assertNotIn("<script>", text)
        self.assertTrue(valid_html(text))

    def test_long_text_is_cut_under_telegram_limit(self):
        r = decorate(evaluate_institutional(frames(UP, (12, -5), 1)))
        r["narrative"] = {"reasoning": "x" * 6000, "macro_context": "y" * 2000, "risk_notice": "z"}
        self.assertLessEqual(len(trader_message(r)), 4100)


if __name__ == "__main__":
    unittest.main()
