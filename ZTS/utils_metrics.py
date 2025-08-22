# ZTS/utils_metrics.py
# ---------------------------------
# Robust helpers for per-round metrics.
# All functions are pure and tolerate missing/empty inputs.

from typing import List, Dict, Tuple, Optional
import math


def compute_roi(start_value: float, end_value: float) -> float:
    """
    Return on investment (simple): (end - start) / start
    Returns 0.0 if start_value <= 0 or invalid.
    """
    try:
        if start_value and start_value > 0:
            return (float(end_value) - float(start_value)) / float(start_value)
    except Exception:
        pass
    return 0.0


def compute_max_drawdown(values: List[float]) -> float:
    """
    Max drawdown on a value/equity curve (as a fraction, <= 0).
    If empty or len<2 -> 0.0 ; if only rises -> 0.0 ; drawdowns are negative.
    """
    if not values or len(values) < 2:
        return 0.0
    peak = values[0]
    max_dd = 0.0  # negative or zero
    for v in values:
        if v > peak:
            peak = v
        dd = (v - peak) / peak if peak else 0.0
        if dd < max_dd:
            max_dd = dd
    return float(max_dd)


def compute_trade_count(trades: List[Dict]) -> int:
    """
    Count executed trades. A trade dict can be minimal: {'qty': int/float, 'price': float, 'side': 'BUY'/'SELL', 'ts': <any>}
    Entries with qty==0 are ignored.
    """
    if not trades:
        return 0
    n = 0
    for t in trades:
        try:
            if abs(float(t.get('qty', 0))) > 0:
                n += 1
        except Exception:
            # malformed trade -> ignore
            pass
    return n


def compute_gross_volume(trades: List[Dict]) -> float:
    """
    Sum of absolute traded notional: sum(|qty| * price).
    Missing price/qty -> treated as 0 for that leg.
    """
    if not trades:
        return 0.0
    vol = 0.0
    for t in trades:
        try:
            q = abs(float(t.get('qty', 0.0)))
            p = float(t.get('price', 0.0))
            vol += q * p
        except Exception:
            pass
    return float(vol)


def compute_turnover(trades: List[Dict], portfolio_values: List[float]) -> float:
    """
    Turnover for the round: gross traded value divided by average portfolio value.
    Returns 0.0 if avg portfolio is not positive.
    """
    gross = compute_gross_volume(trades)
    if portfolio_values:
        # average over positive entries only to avoid divide-by-zero
        vals = [v for v in portfolio_values if isinstance(v, (int, float)) and v > 0]
        avg_pv = sum(vals) / len(vals) if vals else 0.0
    else:
        avg_pv = 0.0
    if avg_pv > 0:
        return float(gross / avg_pv)
    return 0.0


def compute_anchor_deviation_bp(trades: List[Dict], anchors: List[float]) -> float:
    """
    Anchoring deviation (basis points): average over trades of 10,000 * (exec_price - nearest_anchor) / nearest_anchor.
    If no anchors or no valid prices -> 0.0.
    """
    if not trades or not anchors:
        return 0.0
    anchors = [float(a) for a in anchors if isinstance(a, (int, float)) or (isinstance(a, str) and a.replace('.', '', 1).isdigit())]
    if not anchors:
        return 0.0

    def nearest_anchor(p: float) -> Optional[float]:
        try:
            return min(anchors, key=lambda a: abs(a - p)) if anchors else None
        except Exception:
            return None

    diffs = []
    for t in trades:
        try:
            p = float(t.get('price', None))
            if not p or p <= 0:
                continue
            a = nearest_anchor(p)
            if a and a > 0:
                bps = 10000.0 * (p - a) / a
                diffs.append(bps)
        except Exception:
            continue
    if not diffs:
        return 0.0
    # mean absolute deviation in bp (often more interpretable)
    return float(sum(abs(x) for x in diffs) / len(diffs))


def safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def summarize_round(
    *,
    start_value: float,
    end_value: float,
    portfolio_values: List[float],
    trades: List[Dict],
    anchors: List[float]
) -> Dict:
    """
    One-call summary helper that returns all round-level metrics.
    All inputs optional; function guards against missing data gracefully.
    """
    roi = compute_roi(safe_float(start_value), safe_float(end_value))
    max_dd = compute_max_drawdown([safe_float(v) for v in (portfolio_values or [])])
    n_trades = compute_trade_count(trades or [])
    turnover = compute_turnover(trades or [], portfolio_values or [])
    anchor_bp = compute_anchor_deviation_bp(trades or [], anchors or [])

    return dict(
        roi=round(roi, 6),
        max_dd=round(max_dd, 6),              # negative or 0 (e.g., -0.1234 = -12.34%)
        trade_count=int(n_trades),
        turnover=round(turnover, 6),
        anchor_bp=round(anchor_bp, 2),        # avg abs deviation in basis points
    )
