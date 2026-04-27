# 测试文档

本文档说明 A-Stock Agent 的测试体系：覆盖范围、每条用例的验证逻辑，以及如何扩展测试。

---

## 快速运行

```bash
# 安装开发依赖
pip install pytest pandas numpy

# 运行全部测试
pytest tests/ -v

# 运行单个类
pytest tests/test_technical.py::TestCalculateMa -v

# 查看覆盖率（需安装 pytest-cov）
pytest tests/ --cov=a_stock_agent --cov-report=term-missing
```

---

## 测试文件结构

```
tests/
├── __init__.py
├── test_technical.py   # 技术指标单元测试（29 条）
└── TEST-GUIDE.md       # 本文档
```

---

## test_technical.py — 技术指标单元测试（29/29 通过）

所有测试均为纯函数测试，无需网络、无需数据库，毫秒级运行。

### 辅助函数 `make_df(prices)`

```python
def make_df(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        'close': prices,
        'high':  [p * 1.02 for p in prices],
        'low':   [p * 0.98 for p in prices],
        'vol':   [1_000_000.0] * len(prices),
    })
```

构造最简 OHLCV DataFrame，high/low 以 close ±2% 推算，vol 固定为 100 万。所有测试的输入数据均通过此函数生成，保证隔离性。

---

### `TestCalculateMa` — 移动平均线（5 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_ma5_correct_value` | 价格 1..10 | `ma5` 末值 = mean(6,7,8,9,10) = **8.0** |
| `test_ma_nan_when_insufficient_data` | 价格 [10,11,12]，仅3行 | 数据不足5根时，`ma5` 全列应为 NaN |
| `test_multiple_periods_all_present` | 60行价格 | 指定 [5,10,20,60] 后，四列均存在于结果 |
| `test_ma_does_not_modify_original` | 10行平价 | `calculate_ma()` 不应修改原始 DataFrame 的列集合 |
| `test_parametrized_periods` (×3) | 价格 1..10，period=3/5/10 | `pytest.mark.parametrize`：末值 = 对应区间均值，精度 1e-6 |

**核心验证思路**：MA 是滑动窗口均值，测试直接手算期望值做精确对比，同时验证数据不足时的 NaN 边界行为。

---

### `TestCalculateMacd` — MACD 指标（4 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_output_columns_exist` | 30行递增价格 | 结果必须包含 `diff`、`dea`、`macd` 三列 |
| `test_diff_positive_after_sustained_rise` | 前30行平、后10行急涨 | 持续上涨后，EMA12 > EMA26，`diff > 0` |
| `test_diff_negative_after_sustained_fall` | 前30行平、后10行急跌 | 持续下跌后，EMA12 < EMA26，`diff < 0` |
| `test_macd_is_twice_diff_minus_dea` | 40行震荡价格 | 验证公式：`macd = (diff - dea) × 2`，用 `pd.testing.assert_series_equal` 精确比对 |

**核心验证思路**：前两条验证方向性正确，第四条直接验证 MACD 公式的数学定义，确保实现不偏离标准。

---

### `TestCalculateRsi` — RSI 相对强弱指数（4 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_rsi_all_gains_equals_100` | 价格单调递增 | 全为涨无跌，`RSI = 100` |
| `test_rsi_all_losses_equals_0` | 价格单调递减 | 全为跌无涨，`RSI = 0` |
| `test_rsi_within_0_100` | 随机游走50行（seed=42） | 任意价格序列，RSI 必须始终在 [0, 100] 内 |
| `test_rsi_column_named_correctly` | 任意价格，`period=6` | 输出列名为 `rsi6`（动态命名） |

**核心验证思路**：RSI 的两个极端值是可以解析验证的（全涨=100，全跌=0），用极端输入验证公式极限行为，再用随机输入验证值域约束。

---

### `TestCalculateKdj` — KDJ 随机指标（3 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_output_columns` | 19行递增价格 | 结果包含 `kdj_k`、`kdj_d`、`kdj_j` |
| `test_k_d_within_0_100` | 随机游走40行（seed=0） | K 值和 D 值必须在 [0, 100] 内（数学约束） |
| `test_j_can_exceed_bounds` | 单调递增价格 | J = 3K - 2D，设计上**可以**超出 [0, 100]，验证未被错误截断 |

**核心验证思路**：K 和 D 有数学约束（加权平均不出界），J 则是故意不约束的超买超卖信号，第3条测试防止实现错误地对 J 做了 clip。

---

### `TestCalculateBoll` — 布林带（3 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_upper_above_mid_above_lower` | 震荡价格30行 | 任意时刻：`upper ≥ mid ≥ lower`（数学约束） |
| `test_mid_equals_ma20` | 递增价格30行 | 布林中轨 = MA20，与 `calculate_ma()` 输出精确相等 |
| `test_wider_bands_with_larger_std` | 平稳 vs 高波动30行 | 高波动输入的带宽均值 > 低波动输入（标准差越大带越宽） |

**核心验证思路**：第2条用跨函数比对验证两个独立实现的一致性；第3条验证布林带对波动率的响应方向正确。

---

### `TestCalculateVolumeRatio` — 量比（2 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_ratio_above_1_on_high_vol_day` | 前9天量=1M，第10天=3M | `vol_ma5 = mean(1M,1M,1M,1M,3M) = 1.4M`，量比 = 3M/1.4M ≈ **2.14**，精确比对并验证 > 1 |
| `test_volume_ratio_column_exists` | 10行平价 | 输出包含 `volume_ratio` 列 |

**核心验证思路**：量比的期望值手动计算（注意 MA5 包含今日自身，不是前5日均值），通过精确比对防止窗口计算错误。

---

### `TestDetectMaCross` — MA 金叉/死叉检测（4 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_golden_cross_detected` | ma5=[9,9,9,11], ma10=[10,10,10,10] | 最后一根 ma5 从下穿到上 → `golden=True, death=False` |
| `test_death_cross_detected` | ma5=[11,11,11,9], ma10=[10,10,10,10] | 最后一根 ma5 从上穿到下 → `golden=False, death=True` |
| `test_no_cross_when_static` | ma5 始终 > ma10，无穿越 | `golden=False, death=False` |
| `test_returns_none_when_insufficient_data` | 仅1行数据 | 数据不足时返回 `(None, None)` |

**核心验证思路**：金叉/死叉是"前一根不满足，最后一根满足"的状态跃迁，测试数据精心构造了 N-2 到 N-1 的方向变化，并用 `bool()` 转换规避 `numpy.bool_` 与 Python `True` 的 `is` 比较陷阱。

---

### `TestDetectMacdCross` — MACD 金叉/死叉检测（2 条）

| 测试名 | 输入 | 验证逻辑 |
|--------|------|---------|
| `test_golden_cross` | diff=[-0.1,-0.05,-0.01,0.05], dea=[0,0,0,0] | 最后一根 diff 从负穿零轴 → `golden=True` |
| `test_death_cross` | diff=[0.1,0.05,0.01,-0.05], dea=[0,0,0,0] | 最后一根 diff 从正穿零轴 → `death=True` |

**核心验证思路**：测试数据特别设计了 N-2 根（-0.01）仍为负，N-1 根（0.05）才转正，确保检测的是"最后一根"穿越而非更早发生的穿越。

---

## 逻辑验证测试（代码审查阶段执行，非 pytest）

除单元测试外，在代码审查阶段还对 Agent 核心模块做了内联逻辑验证：

### Agent Brain 边界测试

```
bull     → min_score=4,  max_count=15
bear     → min_score=8,  max_count=5
neutral  → min_score=5,  max_count=10
unknown  → min_score=5,  max_count=10
极端叠加（熊市+历史亏损）→ min_score=10（上限12保护正常）
```

验证了在任意输入下 `min_score ∈ [3, 12]`，`max_count ≥ 3`，不会因叠加调整导致逻辑反转。

### NaN 安全测试

```python
_safe_num(float('nan')) == 0.0   # NaN 被正确过滤
_safe_num(12.5)         == 12.5  # 正常值不受影响
_safe_num(None)         == 0.0   # None 被正确过滤
_safe_num(0.0)          == 0.0   # 0.0 不被误过滤（Python 中 0.0 or 0 也是 0）
```

验证了 `or 0` 无法过滤 NaN（因为 Python 中 `float('nan')` 是 truthy）的修复。

### Backtest ValueError 保护

```python
dates.index('20260401')  # 日期不在列表中 → 抛 ValueError → try/except 正确捕获
```

---

## 已知未覆盖区域

| 模块 | 原因 | 建议扩展方向 |
|------|------|-------------|
| `data_fetcher.py` | 依赖外部 API | 用 `unittest.mock.patch` mock `requests.get`，测试解析逻辑和缓存命中/失效 |
| `stock_filter.py` | 需要 K 线数据 | mock `get_daily_data()` 返回固定 DataFrame，测试打分逻辑和 NaN 处理 |
| `agent_memory.py` | 依赖文件 I/O | 用 `tmp_path` fixture 隔离文件，测试版本迁移和统计计算 |
| `agent_brain.py` | 纯函数，易测 | 补充参数化测试，覆盖所有大盘状态×绩效组合的 min_score 期望值 |
| `portfolio_tracker.py` | 依赖文件 I/O | 同 agent_memory，用 `tmp_path` 隔离 |

---

## 测试设计原则

1. **确定性**：所有随机输入使用固定 seed（`np.random.default_rng(42)`），结果可复现
2. **隔离性**：每个测试类只测一个函数，用 `make_df()` 统一构造输入
3. **精确性**：数值比对用 `pytest.approx()` 或 `pd.testing.assert_series_equal()`，不用 `==` 比浮点
4. **边界覆盖**：每个指标至少覆盖正常值、极端值、数据不足三种场景
5. **陷阱记录**：注释中说明 `numpy.bool_` vs Python `bool` 的 `is` 比较陷阱、量比窗口包含今日的计算细节
