from .breakout import (
    evaluate_breakout_confirmation,
    evaluate_fractal_breakout,
    evaluate_ichimoku_breakout,
    evaluate_keltner_breakout,
    evaluate_squeeze_expansion,
)
from .common import (
    build_result,
    build_result_from_groups,
    failed_from_conflicts,
    score_group,
    side,
    status_from_score,
    total_score,
)
from .flow import evaluate_chaikin_flow, evaluate_vwap_reclaim
from .levels import evaluate_poc_rotation
from .reversal import (
    evaluate_keltner_mean_reversion,
    evaluate_morning_star_fib,
    evaluate_obv_divergence,
    evaluate_reversal_cluster,
)
from .trend import (
    evaluate_accumulation_pattern,
    evaluate_anchored_vwap,
    evaluate_fractal_alligator,
    evaluate_hma_ema_trend,
    evaluate_keltner_pullback,
    evaluate_supertrend_psar,
    evaluate_trend_pullback,
)

STRATEGY_EVALUATORS = {
    "trend_pullback": evaluate_trend_pullback,
    "hma_ema_trend": evaluate_hma_ema_trend,
    "breakout_confirmation": evaluate_breakout_confirmation,
    "squeeze_expansion": evaluate_squeeze_expansion,
    "reversal_cluster": evaluate_reversal_cluster,
    "supertrend_psar": evaluate_supertrend_psar,
    "obv_divergence": evaluate_obv_divergence,
    "keltner_pullback": evaluate_keltner_pullback,
    "keltner_breakout": evaluate_keltner_breakout,
    "keltner_mean_reversion": evaluate_keltner_mean_reversion,
    "vwap_reclaim": evaluate_vwap_reclaim,
    "morning_star_fib": evaluate_morning_star_fib,
    "fractal_breakout": evaluate_fractal_breakout,
    "anchored_vwap": evaluate_anchored_vwap,
    "accumulation_pattern": evaluate_accumulation_pattern,
    "poc_rotation": evaluate_poc_rotation,
    "ichimoku_breakout": evaluate_ichimoku_breakout,
    "fractal_alligator": evaluate_fractal_alligator,
    "chaikin_flow": evaluate_chaikin_flow,
}

__all__ = [
    "build_result",
    "build_result_from_groups",
    "failed_from_conflicts",
    "score_group",
    "side",
    "status_from_score",
    "STRATEGY_EVALUATORS",
    "total_score",
]
