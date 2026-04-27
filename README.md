# A-Stock Agent

> A股智能选股系统 · 从规则管道进化为自适应 Agent

---

## 系统定位

本项目经历了两个阶段的演进：

| 阶段 | 定性 | 核心特征 |
|------|------|----------|
| v1 | **Skill（技能管道）** | 固定规则 → 固定输出，无法自我调整 |
| v2 | **初级 Agent** | 感知环境 → 推理决策 → 动态行动 → 记忆学习 |

---

## Skill → Agent：核心差异

### Skill 阶段（v1）的局限

v1 本质上是一条数据流水线：

```
拉行情 ──→ 规则过滤 ──→ 固定打分 ──→ 输出报告
```

所有"决策"都是硬编码阈值（`MA5 > MA10`、`close < 130`、`min_score = 5`……）。  
**给定相同市场数据，永远输出相同结果。无论牛市熊市，推荐逻辑一成不变。**

---

### Agent 阶段（v2）的改进

v2 形成了完整的感知-推理-行动-记录闭环：

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent 闭环                            │
│                                                             │
│  感知                推理              行动          记录    │
│  ──────            ────────          ──────        ──────   │
│  大盘环境    ──→                                             │
│  持仓盈亏    ──→  agent_brain  ──→  动态参数  ──→  记忆      │
│  信号历史    ──→  decide_params     选股执行       更新       │
│  (记忆)                                                     │
└─────────────────────────────────────────────────────────────┘
```

**具体改进如下：**

#### 1. 大盘环境自适应（P0）
- v1：无论牛市熊市每天推荐 10 只，用户自己判断
- v2：实时检测沪指 MA5/MA20/近3日涨跌，自动调整策略
  - 熊市 → `min_score +3`、推荐压缩至 5 只、市值收窄偏防御
  - 牛市 → 适当放宽，推荐扩展至 15 只

#### 2. 历史绩效反哺信号权重（Agent 核心）
- v1：所有信号权重固定，"低位成长"和"MACD金叉"始终贡献相同分数
- v2：`agent_memory` 追踪每个信号的真实盈亏历史
  - 历史均收益 ≥3% 且胜率 ≥65% → 该信号 **+3 分**
  - 历史均收益 ≤-1.5% 或胜率 ≤35% → 该信号 **-2 分**
  - 跑的次数越多，权重越贴近真实市场表现

#### 3. 类别偏好动态调整
- v1：成长/反弹/突破类别一视同仁
- v2：历史平均收益 ≥2% 且胜率 ≥60% 的类别进入优选列表，低表现类别被降权

#### 4. 持仓跟踪闭环（P1）
- v1：推荐完就结束，不知道效果
- v2：每次推荐自动写入 `positions.json`，下次运行时展示每只持仓的盈亏，并触发止盈/止损提示

#### 5. K 线磁盘缓存（P2）
- v1：每次运行对全量股票重新拉取 K 线，遇到网络波动容易失败
- v2：历史 K 线永久缓存，今日数据按天失效，第二次运行速度大幅提升

#### 6. 自动调度 + 多渠道推送（P3）
- v1：需要手动运行脚本
- v2：APScheduler 每个交易日 15:35 自动运行，支持飞书/钉钉/邮件/Server酱推送

---

## 模块架构

```
a_stock_agent/
├── 数据层
│   ├── data_fetcher.py         # 东方财富/新浪/腾讯三源数据 + K线磁盘缓存
│   └── technical_analysis.py  # MA/MACD/KDJ/RSI/Bollinger 指标计算
│
├── 分析层
│   ├── stock_filter.py         # 技术面筛选（接受 agent_params 动态参数）
│   ├── fundamental_analysis.py # PE/PB/ROE/营收增长基本面评分
│   └── news_analysis.py        # 关键词情感分析 + 市场情绪
│
├── Agent 核心
│   ├── agent_memory.py         # 从持仓历史学习信号/类别胜率和均收益
│   └── agent_brain.py          # 综合大盘+记忆，动态输出选股参数
│
├── 执行层
│   ├── run_daily.py            # 主入口：9 步 Agent 闭环
│   ├── portfolio_tracker.py    # 持仓记录/盈亏跟踪/止盈止损提示
│   ├── backtest.py             # 历史回测（无前视偏差）
│   └── scheduler.py            # APScheduler 定时任务
│
└── 推送层
    └── notifier.py             # 飞书/钉钉/邮件/Server酱统一推送
```

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

```bash
cp config.example.py config.py
# 按需修改推送渠道、关注行业等参数
```

### 运行一次选股

```bash
python3 a_stock_agent/run_daily.py
```

### 启动定时调度（每个交易日 15:35 自动运行）

```bash
# 前台运行
python3 a_stock_agent/scheduler.py

# 后台常驻
nohup python3 a_stock_agent/scheduler.py > logs/scheduler.log 2>&1 &
```

### 查看持仓跟踪

持仓记录保存在 `a_stock_agent/reports/positions.json`，每次运行时自动展示盈亏状态。

手动平仓并记录出场价（供 Agent 学习）：

```python
from a_stock_agent.portfolio_tracker import close_position
close_position("600000.SH", exit_price=12.50, reason="止盈")
```

### 手动测试推送

```bash
python3 -c "
import sys; sys.path.insert(0, 'a_stock_agent')
from notifier import notify
notify('测试', '推送配置正常 ✅')
"
```

---

## 推送配置

支持飞书、钉钉、邮件、Server酱，详见 [notifier-readme.md](notifier-readme.md)。

---

## Agent 记忆文件

每次运行后自动生成/更新 `a_stock_agent/reports/agent_memory.json`，记录：

```json
{
  "total_evaluated": 45,
  "win_rate": 0.62,
  "avg_return": 2.3,
  "signal_performance": {
    "低位成长": {"avg_return": 3.1, "win_rate": 0.70, "count": 20},
    "MACD金叉": {"avg_return": 1.8, "win_rate": 0.60, "count": 15}
  },
  "category_performance": {
    "成长": {"avg_return": 3.5, "win_rate": 0.68, "count": 22}
  }
}
```

样本越多，Agent 决策越精准。建议运行至少 **10 个交易日**后，信号权重调整才会开始生效。

---

## 文档

- [消息推送配置指南](notifier-readme.md)
- [策略说明](references/strategy.md)
- [数据源说明](references/data-sources.md)
- [安装指南](references/installation.md)

---

## 风险提示

1. 本系统仅供学习研究，不构成投资建议
2. A 股市场受政策、情绪影响大，任何量化模型均有局限
3. 建议单只仓位不超过 30%，严格执行止盈止损
4. 市场有风险，投资需谨慎

---

## License

MIT
