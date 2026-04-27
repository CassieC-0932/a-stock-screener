# -*- coding: utf-8 -*-
"""
Agent 决策模块

综合大盘环境 + 历史绩效记忆，动态输出本次选股参数。
这是系统从"规则管道"进化为"初级 Agent"的核心：
  感知（market_env + memory） → 推理（decide_params） → 行动（apply_all_filters with params）
"""

import logging

logger = logging.getLogger(__name__)

# 基准参数（无记忆或无大盘信号时使用）
_BASELINE = {
    'min_score': 5,
    'max_count': 10,
    'score_boost': {},          # {signal: delta_score}
    'preferred_categories': [], # [] 表示不限
    'market_cap_range': (30, 500),
}

# 信号历史表现被认为"显著"所需的最小样本量
_MIN_SIGNAL_SAMPLES = 3
_MIN_TOTAL_SAMPLES = 10


def decide_params(market_env: dict, memory: dict) -> dict:
    """
    核心推理函数，返回本次选股参数 + 决策依据。

    返回结构：
    {
      'min_score': int,
      'max_count': int,
      'score_boost': {signal: delta},
      'preferred_categories': [str],
      'market_cap_range': (min, max),
      'rationale': str,        # 给报告展示的决策摘要
      'detail': [str],         # 每条推理步骤（调试用）
    }
    """
    params = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in _BASELINE.items()}
    detail = []

    env_status = market_env.get('status', 'unknown')
    total = memory.get('total_evaluated', 0)
    avg_return = memory.get('avg_return', 0.0)
    win_rate = memory.get('win_rate', 0.5)
    signal_perf = memory.get('signal_performance', {})
    category_perf = memory.get('category_performance', {})

    # ── 第一层：大盘环境 ──────────────────────────────────────────────────────
    if env_status == 'bear':
        params['min_score'] += 3
        params['max_count'] = 5
        params['market_cap_range'] = (50, 300)
        detail.append("熊市：准入门槛+3，推荐压缩至5只，市值收窄至50-300亿（偏防御）")
    elif env_status == 'bull':
        params['min_score'] = max(3, params['min_score'] - 1)
        params['max_count'] = 15
        detail.append("牛市：准入门槛-1，推荐扩展至15只")
    elif env_status == 'neutral':
        detail.append("大盘中性：维持基准参数")
    else:
        detail.append("大盘状态未知：维持基准参数")

    # ── 第二层：历史整体绩效修正 ─────────────────────────────────────────────
    if total >= _MIN_TOTAL_SAMPLES:
        if avg_return < -2:
            params['min_score'] += 2
            detail.append(f"整体历史均收益{avg_return:.1f}%（亏损），额外收紧+2")
        elif avg_return > 4 and win_rate > 0.65:
            params['min_score'] = max(3, params['min_score'] - 1)
            detail.append(f"整体历史均收益{avg_return:.1f}%/胜率{win_rate:.0%}（优秀），适当放宽-1")
        else:
            detail.append(f"历史均收益{avg_return:.1f}%/胜率{win_rate:.0%}，无需额外修正")
    else:
        detail.append(f"历史样本{total}条（<{_MIN_TOTAL_SAMPLES}），暂不调整整体参数")

    # ── 第三层：信号级别加减分 ────────────────────────────────────────────────
    if total >= _MIN_TOTAL_SAMPLES:
        boosted, penalized = [], []
        for sig, perf in signal_perf.items():
            if perf['count'] < _MIN_SIGNAL_SAMPLES:
                continue
            ar, wr = perf['avg_return'], perf['win_rate']
            if ar >= 3.0 and wr >= 0.65:
                params['score_boost'][sig] = 3
                boosted.append(f"{sig}(+3)")
            elif ar >= 1.5 and wr >= 0.55:
                params['score_boost'][sig] = 1
                boosted.append(f"{sig}(+1)")
            elif ar <= -1.5 or wr <= 0.35:
                params['score_boost'][sig] = -2
                penalized.append(f"{sig}(-2)")
        if boosted:
            detail.append(f"历史表现好的信号加分：{', '.join(boosted)}")
        if penalized:
            detail.append(f"历史表现差的信号减分：{', '.join(penalized)}")
        if not boosted and not penalized:
            detail.append("各信号历史表现无显著差异，不调整权重")
    else:
        detail.append("信号样本不足，不调整权重")

    # ── 第四层：类别偏好 ──────────────────────────────────────────────────────
    if total >= _MIN_TOTAL_SAMPLES:
        good = [
            cat for cat, p in category_perf.items()
            if p['avg_return'] >= 2.0 and p['win_rate'] >= 0.60 and p['count'] >= _MIN_SIGNAL_SAMPLES
        ]
        bad = [
            cat for cat, p in category_perf.items()
            if p['avg_return'] <= -1.0 and p['count'] >= _MIN_SIGNAL_SAMPLES
        ]
        if good:
            params['preferred_categories'] = good
            detail.append(f"优选历史表现良好的类别：{good}")
        if bad:
            detail.append(f"历史表现差的类别将被降权（靠 score_boost 间接影响）：{bad}")

    params['detail'] = detail
    params['rationale'] = ' | '.join(detail[:2])  # 报告中只显示前两条
    logger.info("Agent决策完成: min_score=%d, max_count=%d, boost=%s",
                params['min_score'], params['max_count'], params['score_boost'])
    return params
