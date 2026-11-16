import copy
import unittest

from tests.helpers import zigzag_frame
from trading_bot import trader
from trading_bot.trader import AMBIGUOUS_PHRASE, evaluate_institutional, parse_news_items

UP = [(40, 12), (15, -5), (40, 14), (15, -6), (40, 16), (15, -6), (40, 16)]
DOWN = [(40, -12), (15, 5), (40, -14), (15, 6), (40, -16), (15, 6), (40, -16)]


def frames(legs, tail, seed=1):
    def mk(offset, noise):
        return zigzag_frame(legs + [tail], start=100, seed=seed + offset, noise=noise)
    return {"1d": mk(0, 0.3), "4h": mk(100, 0.3), "1h": mk(200, 0.3), "15m": mk(300, 0.2)}


class DecisionRulesTests(unittest.TestCase):
    def test_phrase_is_exact(self):
        self.assertEqual(AMBIGUOUS_PHRASE, "Condiciones ambiguas. Me mantengo fuera del mercado y explico por qué.")

    def test_default_confluence_threshold_is_three_of_five(self):
        for seed in range(1, 25):
            r = evaluate_institutional(frames(UP, (12, -5), seed))
            if r["decision"] != "NO TRADE":
                self.assertGreaterEqual(r["confluence"], 3)
            elif r["confluence"] is not None and r["confluence"] < 3:
                self.assertTrue(r["ambiguous"])
                self.assertIsNone(r["setup"])

    def test_contradictory_timeframes_abstain(self):
        f = frames(UP, (12, -5))
        f["4h"] = zigzag_frame(DOWN, start=140, seed=7, noise=0.3)
        r = evaluate_institutional(f)
        self.assertEqual(r["decision"], "NO TRADE")
        self.assertTrue(r["ambiguous"])
        self.assertIsNone(r["confluence"])
        self.assertTrue(any("contradictoria" in x.lower() or "sin sesgo" in x.lower() for x in r["reasons"]))

    def test_stale_data_never_trades(self):
        r = evaluate_institutional(frames(UP, (12, -5), 1), stale=True)
        self.assertEqual(r["decision"], "NO TRADE")
        self.assertIsNone(r["setup"])

    def test_imminent_high_impact_news_without_direction_abstains(self):
        news = {"high_impact_imminent": True, "sentiment_score": 0.0}
        r = evaluate_institutional(frames(UP, (12, -5), 1), news)
        self.assertEqual(r["decision"], "NO TRADE")
        self.assertTrue(r["ambiguous"])

    def test_missing_required_timeframe(self):
        f = frames(UP, (12, -5))
        del f["4h"]
        with self.assertRaises(ValueError):
            evaluate_institutional(f)

    def test_narrow_range_abstains(self):
        f = frames(UP, (12, -5))
        flat = zigzag_frame([(60, 0.2)], start=100, seed=3, noise=0.05)
        flat["ATR"] = 1.0
        f["4h"] = flat
        r = evaluate_institutional(f)
        self.assertEqual(r["decision"], "NO TRADE")
        self.assertTrue(r["ambiguous"])


class SetupMathTests(unittest.TestCase):
    def _setups(self, legs, tail, expected):
        found = 0
        for seed in range(1, 60):
            r = evaluate_institutional(frames(legs, tail, seed), min_confluence=1)
            if r["decision"] == "NO TRADE":
                self.assertIsNone(r["setup"])
                continue
            found += 1
            self.assertEqual(r["decision"], expected)
            s = r["setup"]
            if expected == "LONG":
                self.assertLess(s["sl"], s["entry"])
                self.assertLess(s["entry"], s["tp1"])
                self.assertLess(s["tp1"], s["tp2"])
            else:
                self.assertGreater(s["sl"], s["entry"])
                self.assertGreater(s["entry"], s["tp1"])
                self.assertGreater(s["tp1"], s["tp2"])
            self.assertGreaterEqual(s["rr2"], 2.0)
            self.assertLessEqual(s["rr2"], 10.01)
            self.assertAlmostEqual(s["profit_tp2_on_risk"], s["rr2"] * 100)
            self.assertAlmostEqual(s["profit_tp2_account"], s["rr2"] * s["risk_pct"])
            self.assertLessEqual(s["entry_low"], s["entry"])
            self.assertGreaterEqual(s["entry_high"], s["entry"])
            self.assertIn("aprox", s["hold"])
        self.assertGreater(found, 0)

    def test_long_levels_are_ordered_and_rr_ok(self):
        self._setups(UP, (12, -5), "LONG")

    def test_short_levels_are_ordered_and_rr_ok(self):
        self._setups(DOWN, (12, 5), "SHORT")

    def test_strict_min_rr_discards_setup(self):
        for seed in range(1, 30):
            r = evaluate_institutional(frames(UP, (12, -5), seed), min_confluence=1, min_rr=50)
            self.assertEqual(r["decision"], "NO TRADE")

    def test_bearish_news_blocks_long_criterion(self):
        for seed in range(1, 30):
            r = evaluate_institutional(frames(UP, (12, -5), seed), {"sentiment_score": -0.9, "sentiment_label": "Negativo"})
            if r["criteria"]:
                self.assertFalse(r["criteria"][5]["ok"])
                return
        self.fail("ningún escenario llegó a evaluar criterios")

    def test_input_frames_are_not_mutated(self):
        f = frames(UP, (12, -5), 2)
        snapshot = {k: v.copy() for k, v in f.items()}
        evaluate_institutional(copy.deepcopy(f))
        for k in f:
            self.assertTrue(f[k].equals(snapshot[k]))


class NewsParsingTests(unittest.TestCase):
    def test_old_and_new_yfinance_formats(self):
        now = 1_800_000_000
        items = [
            {"title": "Fed holds rates", "providerPublishTime": now - 3600},
            {"title": "Antigua", "providerPublishTime": now - 3 * 86400},
            {"content": {"title": "Bitcoin ETF inflows", "summary": "Resumen largo", "pubDate": "2027-01-15T07:00:00Z"}},
            {"nada": 1}, "texto",
        ]
        out = parse_news_items(items, now=now)
        self.assertEqual(len(out), 2)
        self.assertTrue(out[0].startswith("Fed holds rates"))
        self.assertIn("Bitcoin ETF inflows", out[1])

    def test_empty(self):
        self.assertEqual(parse_news_items(None), [])


class HoldTimeTests(unittest.TestCase):
    def test_format_hold(self):
        self.assertIn("horas", trader._format_hold(4))
        self.assertIn("días", trader._format_hold(72))


if __name__ == "__main__":
    unittest.main()
