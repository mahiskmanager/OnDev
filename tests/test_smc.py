import unittest
import numpy as np
import pandas as pd

from trading_bot import smc


def frame(rows):
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], dtype=float)
    df.index = pd.date_range("2026-01-01", periods=len(df), freq="h", tz="UTC")
    df["ATR"] = 1.0
    return df


class SwingTests(unittest.TestCase):
    def test_swing_high_and_low(self):
        highs = [1, 2, 3, 4, 9, 4, 3, 2, 1, 2, 3, 4, 5]
        lows = [h - 1 for h in highs]
        lows[8] = -5
        df = frame([(h - .5, h, l, h - .5) for h, l in zip(highs, lows)])
        sw = smc.swing_points(df, 3)
        self.assertIn(("H", 4), [(s["kind"], s["pos"]) for s in sw])
        self.assertIn(("L", 8), [(s["kind"], s["pos"]) for s in sw])


class StructureTests(unittest.TestCase):
    def test_uptrend_detected_with_bos(self):
        path = [10, 11, 12, 13, 12, 11, 12, 13, 14, 15, 14, 13, 14, 15, 16, 17, 18, 17, 16, 17, 18, 19, 20]
        df = frame([(p - .2, p + .3, p - .3, p) for p in path])
        ms = smc.market_structure(df, n=2)
        self.assertEqual(ms["trend"], "ALCISTA")
        self.assertEqual(ms["effective_trend"], "ALCISTA")

    def test_choch_flips_effective_trend(self):
        path = [10, 11, 12, 13, 12, 11, 12, 13, 14, 15, 14, 13, 14, 15, 16, 17, 16, 15, 14, 12, 10, 8]
        df = frame([(p + .2, p + .3, p - .3, p) for p in path])
        ms = smc.market_structure(df, n=2)
        self.assertEqual(ms["event"], "CHoCH bajista")
        self.assertEqual(ms["event_status"], "CONFIRMADO")
        self.assertEqual(ms["effective_trend"], "LATERAL")


class SmcZoneTests(unittest.TestCase):
    def test_bullish_fvg_open(self):
        rows = [(10, 10.5, 9.5, 10), (10, 11, 9.9, 10.9), (11, 13, 10.9, 12.8), (12.8, 13.2, 12.5, 13)]
        df = frame(rows)
        zones = smc.fair_value_gaps(df, 1.0)
        self.assertTrue(any(z["side"] == "BULLISH" and abs(z["low"] - 10.5) < 1e-9 and abs(z["high"] - 10.9) < 1e-9 for z in zones))

    def test_filled_fvg_is_dropped(self):
        rows = [(10, 10.5, 9.5, 10), (10, 11, 9.9, 10.9), (11, 13, 10.9, 12.8), (12.8, 12.9, 10.0, 10.2)]
        zones = smc.fair_value_gaps(frame(rows), 1.0)
        self.assertFalse(any(z["side"] == "BULLISH" for z in zones))

    def test_bullish_order_block(self):
        rows = [(10, 10.2, 9.8, 10), (10, 10.1, 9.4, 9.5), (9.5, 12.5, 9.5, 12.2), (12.2, 12.9, 12.0, 12.8), (12.8, 13, 12.5, 12.9)]
        obs = smc.order_blocks(frame(rows), 1.0)
        self.assertTrue(any(o["side"] == "BULLISH" and abs(o["low"] - 9.4) < 1e-9 for o in obs))

    def test_liquidity_sweep_of_lows(self):
        base = [10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 12, 11, 10.5]
        rows = [(p, p + .3, p - .3, p) for p in base]
        rows.append((10.4, 10.6, 8.5, 10.5))  # perfora el mínimo 8.7 y cierra arriba
        sweeps = smc.liquidity_sweeps(frame(rows), n=2, window=3)
        self.assertTrue(any(s["side"] == "LOW" and s["bias"] == "BULLISH" for s in sweeps))

    def test_premium_discount_zones(self):
        base = [10, 12, 14, 16, 14, 12, 10, 12, 14, 16, 18, 16, 14, 12]
        df = frame([(p, p + .2, p - .2, p) for p in base])
        pdz = smc.premium_discount(df, n=2)
        self.assertIsNotNone(pdz)
        expected = "DESCUENTO" if pdz["position"] < 0.45 else ("PREMIUM" if pdz["position"] > 0.55 else "EQUILIBRIO")
        self.assertEqual(pdz["zone"], expected)
        self.assertLess(pdz["low"], pdz["high"])


class LevelTests(unittest.TestCase):
    def test_confluence_clusters_levels(self):
        base = [10, 12, 14, 12, 10, 12, 14, 12, 10, 12, 13]
        df = frame([(p, p + .2, p - .2, p) for p in base])
        sr = smc.support_resistance(df, 12.5, 1.0, {"EMA 50": 14.1, "VWAP": 9.9}, n=2)
        best = sr["strongest"]
        self.assertGreaterEqual(best["strength"], 2)
        self.assertTrue(all(z["price"] < 12.5 for z in sr["supports"]))
        self.assertTrue(all(z["price"] > 12.5 for z in sr["resistances"]))

    def test_vwap_none_without_volume(self):
        df = frame([(10, 11, 9, 10)] * 5)
        df["Volume"] = 0.0
        self.assertIsNone(smc.vwap(df))
        df["Volume"] = 100.0
        self.assertAlmostEqual(smc.vwap(df), 10.0)

    def test_fib_levels(self):
        levels = smc.fib_levels(110, 100)
        self.assertAlmostEqual(levels["Fib 0.5"], 105)


class PatternTests(unittest.TestCase):
    def test_double_top(self):
        path = [10, 12, 14, 16, 14, 12, 10, 12, 14, 16, 14, 12, 11, 10, 9]
        df = frame([(p, p + .2, p - .2, p) for p in path])
        names = [p["name"] for p in smc.chart_patterns(df, 1.0, n=2)]
        self.assertIn("Doble techo", names)

    def test_double_bottom(self):
        path = [20, 18, 16, 14, 16, 18, 20, 18, 16, 14, 16, 18, 19, 21, 22]
        df = frame([(p, p + .2, p - .2, p) for p in path])
        names = [p["name"] for p in smc.chart_patterns(df, 1.0, n=2)]
        self.assertIn("Doble suelo", names)

    def test_bearish_divergence(self):
        path = [10, 12, 14, 12, 10, 12, 15, 12, 10]
        df = frame([(p, p + .2, p - .2, p) for p in path])
        df["RSI"] = [50, 60, 75, 60, 50, 60, 65, 55, 50]
        self.assertEqual(smc.divergence(df, "RSI", n=2), "BEARISH")


if __name__ == "__main__":
    unittest.main()
