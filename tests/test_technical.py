# -*- coding: utf-8 -*-
"""
技术指标计算函数单元测试

运行：pytest tests/
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from technical_analysis import (
    calculate_ma,
    calculate_macd,
    calculate_kdj,
    calculate_rsi,
    calculate_boll,
    calculate_volume_ratio,
    detect_ma_cross,
    detect_macd_cross,
)


# ── 测试辅助 ──────────────────────────────────────────────────────────────────

def make_df(prices: list[float]) -> pd.DataFrame:
    """构造最小 OHLCV DataFrame"""
    return pd.DataFrame({
        'close': prices,
        'high':  [p * 1.02 for p in prices],
        'low':   [p * 0.98 for p in prices],
        'vol':   [1_000_000.0] * len(prices),
    })


# ── calculate_ma ──────────────────────────────────────────────────────────────

class TestCalculateMa:
    def test_ma5_correct_value(self):
        df = make_df(list(range(1, 11)))          # 1..10
        result = calculate_ma(df, [5])
        # 最后5个 = 6,7,8,9,10 → mean = 8
        assert result['ma5'].iloc[-1] == pytest.approx(8.0)

    def test_ma_nan_when_insufficient_data(self):
        df = make_df([10.0, 11.0, 12.0])          # 只有3行，MA5 全为 NaN
        result = calculate_ma(df, [5])
        assert result['ma5'].isna().all()

    def test_multiple_periods_all_present(self):
        df = make_df([float(i) for i in range(1, 61)])
        result = calculate_ma(df, [5, 10, 20, 60])
        for col in ['ma5', 'ma10', 'ma20', 'ma60']:
            assert col in result.columns

    def test_ma_does_not_modify_original(self):
        df = make_df([10.0] * 10)
        original_cols = set(df.columns)
        calculate_ma(df, [5])
        assert set(df.columns) == original_cols  # 原始 df 不变

    @pytest.mark.parametrize("period,expected", [
        (3, 10.0),   # mean(8,9,10) = 9, but prices are [1..10] → last 3 = 8,9,10 → 9
        (5, 8.0),
        (10, 5.5),
    ])
    def test_parametrized_periods(self, period, expected):
        df = make_df(list(range(1, 11)))
        result = calculate_ma(df, [period])
        # last `period` values of 1..10
        last_n = list(range(11 - period, 11))
        assert result[f'ma{period}'].iloc[-1] == pytest.approx(sum(last_n) / period)


# ── calculate_macd ────────────────────────────────────────────────────────────

class TestCalculateMacd:
    def test_output_columns_exist(self):
        df = make_df([float(i) for i in range(1, 31)])
        result = calculate_macd(df)
        for col in ['diff', 'dea', 'macd']:
            assert col in result.columns

    def test_diff_positive_after_sustained_rise(self):
        prices = [10.0] * 30 + [15.0] * 10
        df = make_df(prices)
        result = calculate_macd(df)
        assert result['diff'].iloc[-1] > 0

    def test_diff_negative_after_sustained_fall(self):
        prices = [15.0] * 30 + [10.0] * 10
        df = make_df(prices)
        result = calculate_macd(df)
        assert result['diff'].iloc[-1] < 0

    def test_macd_is_twice_diff_minus_dea(self):
        df = make_df([float(i % 5 + 10) for i in range(40)])
        result = calculate_macd(df)
        expected = (result['diff'] - result['dea']) * 2
        pd.testing.assert_series_equal(result['macd'], expected, check_names=False)


# ── calculate_rsi ─────────────────────────────────────────────────────────────

class TestCalculateRsi:
    def test_rsi_all_gains_equals_100(self):
        df = make_df([float(i) for i in range(1, 20)])
        result = calculate_rsi(df, period=14)
        assert result['rsi14'].iloc[-1] == pytest.approx(100.0)

    def test_rsi_all_losses_equals_0(self):
        df = make_df([float(20 - i) for i in range(20)])
        result = calculate_rsi(df, period=14)
        assert result['rsi14'].iloc[-1] == pytest.approx(0.0)

    def test_rsi_within_0_100(self):
        rng = np.random.default_rng(42)
        prices = list(10 + rng.uniform(-1, 1, 50).cumsum())
        df = make_df(prices)
        result = calculate_rsi(df, period=14)
        valid = result['rsi14'].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_column_named_correctly(self):
        df = make_df([float(i) for i in range(1, 20)])
        result = calculate_rsi(df, period=6)
        assert 'rsi6' in result.columns


# ── calculate_kdj ─────────────────────────────────────────────────────────────

class TestCalculateKdj:
    def test_output_columns(self):
        df = make_df([float(i) for i in range(1, 20)])
        result = calculate_kdj(df)
        for col in ['kdj_k', 'kdj_d', 'kdj_j']:
            assert col in result.columns

    def test_k_d_within_0_100(self):
        rng = np.random.default_rng(0)
        prices = list(10 + rng.uniform(-0.5, 0.5, 40).cumsum())
        df = make_df(prices)
        result = calculate_kdj(df)
        assert result['kdj_k'].between(0, 100).all()
        assert result['kdj_d'].between(0, 100).all()

    def test_j_can_exceed_bounds(self):
        # J = 3K - 2D 可超出 [0,100]
        df = make_df([float(i) for i in range(1, 30)])
        result = calculate_kdj(df)
        assert not result['kdj_j'].between(0, 100).all()


# ── calculate_boll ────────────────────────────────────────────────────────────

class TestCalculateBoll:
    def test_upper_above_mid_above_lower(self):
        prices = [float(i % 5 + 10) for i in range(30)]
        df = make_df(prices)
        result = calculate_boll(df).dropna()
        assert (result['boll_upper'] >= result['boll_mid']).all()
        assert (result['boll_mid'] >= result['boll_lower']).all()

    def test_mid_equals_ma20(self):
        prices = [float(i) for i in range(1, 31)]
        df = make_df(prices)
        result = calculate_boll(df, period=20)
        ma_result = calculate_ma(df, [20])
        pd.testing.assert_series_equal(
            result['boll_mid'].dropna(),
            ma_result['ma20'].dropna(),
            check_names=False
        )

    def test_wider_bands_with_larger_std(self):
        flat = make_df([10.0] * 30)
        volatile = make_df([10.0 + (i % 3) * 5 for i in range(30)])
        flat_r = calculate_boll(flat).dropna()
        vol_r = calculate_boll(volatile).dropna()
        flat_width = (flat_r['boll_upper'] - flat_r['boll_lower']).mean()
        vol_width = (vol_r['boll_upper'] - vol_r['boll_lower']).mean()
        assert vol_width > flat_width


# ── calculate_volume_ratio ────────────────────────────────────────────────────

class TestCalculateVolumeRatio:
    def test_ratio_above_1_on_high_vol_day(self):
        # 前9天量均为1M，第10天为3M
        # vol_ma5 = mean(1M,1M,1M,1M,3M) = 1.4M → ratio = 3M/1.4M ≈ 2.14
        vols = [1_000_000.0] * 9 + [3_000_000.0]
        prices = [10.0] * 10
        df = make_df(prices)
        df['vol'] = vols
        result = calculate_volume_ratio(df)
        ma5_last = sum(vols[-5:]) / 5
        expected = vols[-1] / ma5_last
        assert result['volume_ratio'].iloc[-1] == pytest.approx(expected, rel=0.01)
        assert result['volume_ratio'].iloc[-1] > 1.0   # 今日量高于均量

    def test_volume_ratio_column_exists(self):
        df = make_df([10.0] * 10)
        result = calculate_volume_ratio(df)
        assert 'volume_ratio' in result.columns


# ── detect_ma_cross ───────────────────────────────────────────────────────────

class TestDetectMaCross:
    def _with_mas(self, ma5_vals: list, ma10_vals: list) -> pd.DataFrame:
        df = pd.DataFrame({'ma5': ma5_vals, 'ma10': ma10_vals})
        return df

    def test_golden_cross_detected(self):
        # ma5 在最后一根从低于 ma10 穿越到高于 ma10
        # [-2]: ma5=9 <= ma10=10  [-1]: ma5=11 > ma10=10
        df = self._with_mas([9, 9, 9, 11], [10, 10, 10, 10])
        golden, death = detect_ma_cross(df)
        assert bool(golden) is True
        assert bool(death) is False

    def test_death_cross_detected(self):
        # [-2]: ma5=11 >= ma10=10  [-1]: ma5=9 < ma10=10
        df = self._with_mas([11, 11, 11, 9], [10, 10, 10, 10])
        golden, death = detect_ma_cross(df)
        assert bool(golden) is False
        assert bool(death) is True

    def test_no_cross_when_static(self):
        df = self._with_mas([11, 11, 11], [10, 10, 10])
        golden, death = detect_ma_cross(df)
        assert bool(golden) is False
        assert bool(death) is False

    def test_returns_none_when_insufficient_data(self):
        df = self._with_mas([10], [9])
        golden, death = detect_ma_cross(df)
        assert golden is None and death is None


# ── detect_macd_cross ─────────────────────────────────────────────────────────

class TestDetectMacdCross:
    def _with_macd(self, diff_vals: list, dea_vals: list) -> pd.DataFrame:
        return pd.DataFrame({'diff': diff_vals, 'dea': dea_vals})

    def test_golden_cross(self):
        # [-2]: diff=-0.01 <= dea=0  [-1]: diff=0.05 > dea=0 → 金叉
        df = self._with_macd([-0.1, -0.05, -0.01, 0.05], [0.0, 0.0, 0.0, 0.0])
        golden, death = detect_macd_cross(df)
        assert bool(golden) is True

    def test_death_cross(self):
        # [-2]: diff=0.01 >= dea=0  [-1]: diff=-0.05 < dea=0 → 死叉
        df = self._with_macd([0.1, 0.05, 0.01, -0.05], [0.0, 0.0, 0.0, 0.0])
        golden, death = detect_macd_cross(df)
        assert bool(death) is True
