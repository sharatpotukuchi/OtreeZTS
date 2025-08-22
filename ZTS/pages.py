from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import locale
from urllib.parse import urlencode

# Round-metrics helper (includes Sharpe & Sortino)
from .utils_metrics import summarize_round


class InstructionPage(Page):
    def is_displayed(self):
        return self.round_number == 1


class StartPage(Page):
    def is_displayed(self):
        return self.round_number <= self.session.num_rounds

    def vars_for_template(self):
        is_training_round = self.session.config['training_round'] and self.round_number == 1
        return dict(is_training_round=is_training_round)


class TradingPage(Page):
    live_method = 'live_trading_report'

    def is_displayed(self):
        return self.round_number <= self.session.num_rounds

    def js_vars(self):
        """
        Pass data for trading controller to javascript front-end
        """
        asset, prices, news = self.subsession.get_timeseries_values()
        return dict(
            refresh_rate=self.subsession.get_config_multivalue('refresh_rate_ms'),
            graph_buffer=self.session.config['graph_buffer'],
            prices=prices,
            news=news,
            asset=asset,
            cash=self.subsession.get_config_multivalue('initial_cash'),
            shares=self.subsession.get_config_multivalue('initial_shares'),
            trading_button_values=self.subsession.get_config_multivalue('trading_button_values'),
        )


class ResultsPage(Page):
    def is_displayed(self):
        return self.round_number <= self.session.num_rounds

    def to_human_readable(self, x):
        return '{:,}'.format(int(x))

    def vars_for_template(self):
        return dict(
            cash=self.to_human_readable(self.player.cash),
            shares=self.to_human_readable(self.player.shares),
            share_value=self.to_human_readable(self.player.share_value),
            portfolio_value=self.to_human_readable(self.player.portfolio_value),
            pandl=self.to_human_readable(self.player.pandl),
        )

    # Compute per-round features (incl. Sharpe/Sortino) just before moving on
    def before_next_page(self):
        p = self.participant
        s = self.session

        # ---- Gather inputs for metrics (tolerate missing data) ----
        pv_series = (
            getattr(self.player, 'portfolio_values_series', None)
            or p.vars.get('pv_series_round', None)
            or []
        )
        start_value = pv_series[0] if pv_series else getattr(self.player, 'portfolio_value_start', None)
        end_value = pv_series[-1] if pv_series else getattr(self.player, 'portfolio_value', None)

        trades = (
            getattr(self.player, 'trades_log_round', None)
            or p.vars.get('trades_log_round', None)
            or []
        )

        anchors = (
            getattr(self.player, 'anchors_round', None)
            or p.vars.get('anchors_round', None)
            or []
        )

        # Optional annualisation controls from settings (totally optional)
        periods_per_year = s.config.get('metrics_periods_per_year', None)   # e.g., 252*6 if ~6 updates/day, etc.
        rf_annual = s.config.get('metrics_rf_annual', 0.0)                  # e.g., 0.02 for 2%

        # ---- Compute metrics
        summary = summarize_round(
            start_value=start_value or 0.0,
            end_value=end_value or 0.0,
            portfolio_values=pv_series or [],
            trades=trades or [],
            anchors=anchors or [],
            rf_annual=rf_annual,
            periods_per_year=periods_per_year,
        )

        # Store on player for immediate use by the redirect page
        self.player.roi_round = summary['roi']
        self.player.max_dd_round = summary['max_dd']
        self.player.trade_count_round = summary['trade_count']
        self.player.turnover_round = summary['turnover']
        self.player.anchor_dev_bp_round = summary['anchor_bp']
        self.player.sharpe_round = summary['sharpe']
        self.player.sortino_round = summary['sortino']

        # Also stash in participant.vars if you prefer reading from there
        p.vars['last_round_features'] = dict(
            roi=summary['roi'],
            max_dd=summary['max_dd'],
            trades=summary['trade_count'],
            turnover=summary['turnover'],
            anchor_bp=summary['anchor_bp'],
            sharpe=summary['sharpe'],
            sortino=summary['sortino'],
        )


# === Between-round redirect (both arms) ===
class BetweenRoundQualtrics(Page):
    """
    After EACH round except the last, redirect all participants to Qualtrics.
    Qualtrics branches on ?arm=treatment|control to show either:
      - treatment: questions + GPT nudge
      - control: questions only
    Qualtrics must redirect back to ?return_to=... (we pass it here).
    """
    timeout_seconds = 2  # brief pause; meta-refresh handles the redirect

    def is_displayed(self):
        not_last_round = self.round_number < self.session.num_rounds
        has_link = bool(self.session.config.get('nudge_link_round'))  # per-round Qualtrics link
        return not_last_round and has_link

    def vars_for_template(self):
        p = self.participant
        s = self.session

        arm = p.vars.get('arm', 'control')  # default to control if not set

        # Use the metrics computed in ResultsPage.before_next_page
        features = dict(
            roi=round(getattr(self.player, 'roi_round', 0.0), 6),
            max_dd=round(getattr(self.player, 'max_dd_round', 0.0), 6),
            trades=int(getattr(self.player, 'trade_count_round', 0)),
            turnover=round(getattr(self.player, 'turnover_round', 0.0), 6),
            anchor_bp=round(getattr(self.player, 'anchor_dev_bp_round', 0.0), 2),
            sharpe=round(getattr(self.player, 'sharpe_round', 0.0), 6),
            sortino=round(getattr(self.player, 'sortino_round', 0.0), 6),
        )
        p.vars['last_round_features'] = features

        # Return URL: the next oTree page in sequence
        return_url = self._url_next

        # Base Qualtrics link for the BETWEEN-ROUND block
        q_base = s.config.get('nudge_link_round')

        params = dict(
            PROLIFIC_PID=p.vars.get('PROLIFIC_PID', 'NA'),
            session=p.code,
            arm=arm,                                # Qualtrics branches on this
            round=self.round_number,
            roi=features['roi'],
            max_dd=features['max_dd'],
            trades=features['trades'],
            turnover=features['turnover'],
            anchor_bp=features['anchor_bp'],
            sharpe=features['sharpe'],
            sortino=features['sortino'],
            return_to=return_url,                   # Qualtrics end-of-block redirects here
        )
        q_url = f"{q_base}?{urlencode(params)}"
        return dict(q_url=q_url)


# Keep the order so the redirect happens AFTER results and BEFORE the next round.
page_sequence = [
    InstructionPage,
    StartPage,
    TradingPage,
    ResultsPage,
    BetweenRoundQualtrics,   # always between rounds; Qualtrics handles arm branching
]
