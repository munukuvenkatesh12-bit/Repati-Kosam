"""
Unit tests for the Technical Analysis engine.
Run: pytest tests/test_ta_engine.py -v
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ta_engine import (
    compute_ema, compute_atr, find_fractals, cluster_levels,
    compute_stop_loss, compute_bull_bear_zones, resample_weekly,
)


class TestEMA:
    def test_constant_series(self):
        """EMA of a constant series should equal that constant."""
        closes = [100.0] * 50
        ema = compute_ema(closes, 20)
        assert all(abs(v - 100.0) < 0.001 for v in ema)

    def test_first_value(self):
        """First EMA value should equal first close."""
        closes = [10.0, 20.0, 30.0, 40.0, 50.0]
        ema = compute_ema(closes, 3)
        assert ema[0] == 10.0

    def test_trending_up(self):
        """EMA should lag behind an uptrend."""
        closes = [float(i) for i in range(1, 21)]
        ema = compute_ema(closes, 5)
        # EMA should be less than close in an uptrend
        assert ema[-1] < closes[-1]

    def test_length_matches(self):
        """Output length should match input length."""
        closes = [10.0, 20.0, 30.0, 40.0, 50.0]
        ema = compute_ema(closes, 3)
        assert len(ema) == len(closes)


class TestATR:
    def test_single_candle(self):
        """ATR of one candle with enough padding should work."""
        highs = [110.0] * 14
        lows = [100.0] * 14
        closes = [105.0] * 14
        atr = compute_atr(highs, lows, closes, 14)
        # First 13 are None, 14th is average TR
        assert atr[13] == 10.0

    def test_none_prefix(self):
        """First (period-1) values should be None."""
        highs = [110.0] * 20
        lows = [100.0] * 20
        closes = [105.0] * 20
        atr = compute_atr(highs, lows, closes, 14)
        assert all(v is None for v in atr[:13])
        assert atr[13] is not None

    def test_length(self):
        atr = compute_atr([10] * 30, [5] * 30, [7] * 30, 14)
        assert len(atr) == 30


class TestFractals:
    def test_v_shape(self):
        """A V-shaped pattern should detect the bottom as a swing low."""
        # Create V: 10, 8, 6, 4, 2, 4, 6, 8, 10
        highs = [10, 8, 6, 4, 2, 4, 6, 8, 10]
        lows = [10, 8, 6, 4, 2, 4, 6, 8, 10]
        sh, sl = find_fractals(highs, lows, window=3)
        # Index 4 (value 2) should be a swing low
        swing_low_indices = [idx for idx, _ in sl]
        assert 4 in swing_low_indices

    def test_peak(self):
        """An inverted V should detect the peak as a swing high."""
        highs = [2, 4, 6, 8, 10, 8, 6, 4, 2]
        lows = [2, 4, 6, 8, 10, 8, 6, 4, 2]
        sh, sl = find_fractals(highs, lows, window=3)
        swing_high_indices = [idx for idx, _ in sh]
        assert 4 in swing_high_indices


class TestClustering:
    def test_merge_close_prices(self):
        """Prices within 1.5% should merge."""
        prices = [100.0, 100.5, 101.0, 100.8]  # All within 1.5% of each other
        clusters = cluster_levels(prices, tolerance=0.015, min_touches=2)
        assert len(clusters) == 1
        assert clusters[0]["strength"] == 4

    def test_separate_distant_prices(self):
        """Prices far apart should not merge."""
        prices = [100.0, 100.5, 200.0, 200.5]
        clusters = cluster_levels(prices, tolerance=0.015, min_touches=2)
        assert len(clusters) == 2

    def test_min_touches(self):
        """Single-touch levels should be filtered out."""
        prices = [100.0, 200.0]  # Each appears once
        clusters = cluster_levels(prices, tolerance=0.015, min_touches=2)
        assert len(clusters) == 0

    def test_empty_input(self):
        assert cluster_levels([], tolerance=0.015) == []


class TestStopLoss:
    def test_below_current_price(self):
        """Stop loss should be below current price for normal stocks."""
        highs = [100 + i * 0.5 for i in range(50)]
        lows = [98 + i * 0.5 for i in range(50)]
        closes = [99 + i * 0.5 for i in range(50)]
        atr = compute_atr(highs, lows, closes, 14)
        sl = compute_stop_loss(highs, lows, closes, atr)
        assert sl["stop_loss"] < closes[-1]
        assert sl["risk_pct"] > 0

    def test_fallback_for_downtrend(self):
        """Stop loss should use fallback when primary exceeds price."""
        # Strongly declining stock
        highs = [100 - i * 2 for i in range(50)]
        lows = [95 - i * 2 for i in range(50)]
        closes = [97 - i * 2 for i in range(50)]
        atr = compute_atr(highs, lows, closes, 14)
        sl = compute_stop_loss(highs, lows, closes, atr)
        assert sl["stop_loss"] < closes[-1]


class TestBullBear:
    def test_golden_cross(self):
        """Rising prices should eventually produce a bull zone."""
        closes = [float(i) for i in range(100)]
        dates = [f"2026-{(i // 30) + 1:02d}-{(i % 28) + 1:02d}" for i in range(100)]
        zones = compute_bull_bear_zones(closes, dates)
        # Should end in a bull zone since EMA20 > EMA50 when prices trend up
        assert zones[-1]["type"] == "bull"

    def test_returns_at_least_one_zone(self):
        closes = [100.0] * 50
        dates = [f"2026-01-{i + 1:02d}" for i in range(50)]
        zones = compute_bull_bear_zones(closes, dates)
        assert len(zones) >= 1


class TestWeeklyResample:
    def test_five_daily_to_one_weekly(self):
        """5 weekday candles should produce 1 weekly candle."""
        candles = [
            {"date": "2026-01-05", "open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
            {"date": "2026-01-06", "open": 105, "high": 115, "low": 100, "close": 110, "volume": 1200},
            {"date": "2026-01-07", "open": 110, "high": 120, "low": 105, "close": 108, "volume": 800},
            {"date": "2026-01-08", "open": 108, "high": 112, "low": 102, "close": 111, "volume": 900},
            {"date": "2026-01-09", "open": 111, "high": 118, "low": 106, "close": 115, "volume": 1100},
        ]
        weekly = resample_weekly(candles)
        assert len(weekly) == 1
        assert weekly[0]["open"] == 100      # First open
        assert weekly[0]["high"] == 120      # Max high
        assert weekly[0]["low"] == 95        # Min low
        assert weekly[0]["close"] == 115     # Last close
        assert weekly[0]["volume"] == 5000   # Sum volume
