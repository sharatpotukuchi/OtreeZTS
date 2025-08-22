# ZTS/utils_metrics.py
# ---------------------------------
# Robust helpers for per-round metrics.
# All functions are pure and tolerate missing/empty inputs.

from typing import List, Dict, Tuple, Optional
import math


def safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


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
        vals = [v for v in portfolio_values if isinstance(v, (int, float)) and v > 0]
        avg_pv = sum(vals) / len(vals) if vals else 0.0
    else:
        avg_pv = 0.0
    if avg_pv > 0:
        return float(gross / avg_pv)
    return 0.0


def returns_from_values(values: List[float]) -> List[float]:
    """
    Convert a value/equity curve into a simple returns series r_t = (v_t / v_{t-1}) - 1.
    Ignores zero/invalid values safely.
    """
    if not values or len(values) < 2:
        return []
    rets = []
    prev = None
    for v in values:
        v = safe_float(v, None)
        if prev is not None and v and v > 0 and prev > 0:
            rets.append((v / prev) - 1.0)
        prev = v
    return rets


def compute_sharpe_sortino(
    returns: List[float],
    rf_annual: float = 0.0,
    periods_per_year: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Sharpe and Sortino from a returns series.
    - returns: list of per-period simple returns (e.g., per tick or per update).
    - rf_annual: annual risk-free rate as a decimal (e.g., 0.02 for 2%). Default 0.0.
    - periods_per_year: if provided, we annualise (sqrt(T) scaling) and convert rf to per-period.
                        if omitted, we compute non-annualised ratios on the raw returns.

    Returns: (sharpe, sortino). If insufficient data or zero denom, returns 0.0 safely.
    """
    if not returns:
        return 0.0, 0.0

    # Risk-free per period
    if periods_per_year and periods_per_year > 0:
        try:
            rf_per = (1.0 + float(rf_annual)) ** (1.0 / float(periods_per_year)) - 1.0
        except Exception:
            rf_per = 0.0
    else:
        rf_per = 0.0

    # Excess returns
    ex = [(r - rf_per) for r in returns if isinstance(r, (int, float))]
    if len(ex) < 2:
        return 0.0, 0.0

    # Moments
    mean_ex = sum(ex) / len(ex)
    # sample std (unbiased) with ddof=1 when len>1, else population
    var = sum((r - mean_ex) ** 2 for r in ex) / (len(ex) - 1) if len(ex) > 1 else 0.0
    std = math.sqrt(var) if var > 0 else 0.0

    # downside std (only negative excess)
    downs = [r for r in ex if r < 0]
    if len(downs) > 1:
        d_mean = sum(downs) / len(downs)
        d_var = sum((r - d_mean) ** 2 for r in downs) / (len(downs) - 1)
        d_std = math.sqrt(d_var) if d_var > 0 else 0.0
    elif len(downs) == 1:
        d_std = 0.0
    else:
        d_std = 0.0

    sharpe = (mean_ex / std) if std > 0 else 0.0
    sortino = (mean_ex / d_std) if d_std > 0 else 0.0

    # Annualise if we know the frequency
    if periods_per_year and periods_per_year > 0:
        scale = math.sqrt(float(periods_per_year))
        sharpe *= scale
        sortino *= scale

    # guard against NaNs/infs
    if not math.isfinite(sharpe):
        sharpe = 0.0
    if not math.isfinite(sortino):
        sortino = 0.0

    return float(sharpe), float(sortino)


def compute_anchor_deviation_bp(trades: List[Dict], anchors: List[float]) -> float:
    """
    Anchoring deviation (basis points): average over trades of 10,000 * (exec_price - nearest_anchor) / nearest_anchor.
    If no anchors or no valid prices -> 0.0. Uses mean absolute deviation for robustness.
    """
    if not trades or not anchors:
        return 0.0
    # normalise anchors to floats
    norm_anchors = []
    for a in anchors:
        try:
            norm_anchors.append(float(a))
        except Exception:
            try:
                if isinstance(a, str):
                    norm_anchors.append(float(a.strip().replace(',', '')))
            except Exception:
                pass
    anchors = [a for a in norm_anchors if a > 0]
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
                diffs.append(abs(bps))
        except Exception:
            continue
    if not diffs:
        return 0.0
    return float(sum(diffs) / len(diffs))


def summarize_round(
    *,
    start_value: float,
    end_value: float,
    portfolio_values: List[float],
    trades: List[Dict],
    anchors: List[float],
    rf_annual: float = 0.0,
    periods_per_year: Optional[int] = None,
) -> Dict:
    """
    One-call summary helper that returns all round-level metrics.
    If 'periods_per_year' is provided, Sharpe/Sortino are annualised; otherwise left in raw (per-period) units.
    """
    pv = [safe_float(v) for v in (portfolio_values or [])]
    roi = compute_roi(safe_float(start_value), safe_float(end_value))
    max_dd = compute_max_drawdown(pv)
    n_trades = compute_trade_count(trades or [])
    turnover = compute_turnover(trades or [], pv)
    anchor_bp = compute_anchor_deviation_bp(trades or [], anchors or [])

    rets = returns_from_values(pv)
    sharpe, sortino = compute_sharpe_sortino(rets, rf_annual=rf_annual, periods_per_year=periods_per_year)

    return dict(
        roi=round(roi, 6),
        max_dd=round(max_dd, 6),             # negative or 0 (e.g., -0.1234 = -12.34%)
        trade_count=int(n_trades),
        turnover=round(turnover, 6),
        anchor_bp=round(anchor_bp, 2),
        sharpe=round(sharpe, 6),
        sortino=round(sortino, 6),
    )
