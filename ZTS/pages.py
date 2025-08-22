from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
import locale
from urllib.parse import urlencode


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


# === NEW: single between-round redirect (both arms) ===
class BetweenRoundQualtrics(Page):
    """
    After EACH round except the last, redirect all participants to Qualtrics.
    Qualtrics branches on ?arm=treatment|control to show either:
      - treatment: questions + GPT nudge
      - control: questions only
    Qualtrics must redirect back to ?return_to=... (we pass it here).
    """
    timeout_seconds = 2  # show a beat; meta-refresh handles the redirect

    def is_displayed(self):
        not_last_round = self.round_number < self.session.num_rounds
        has_link = bool(self.session.config.get('nudge_link_round'))  # per-round Qualtrics link
        return not_last_round and has_link

    def vars_for_template(self):
        p = self.participant
        s = self.session

        arm = p.vars.get('arm', 'control')  # default to control if not set

        # ===== TODO: replace placeholders with real per-round feature computations =====
        # You can set these on `self.player` at end of trade loop, or compute here from logs.
        features = dict(
            roi=round(getattr(self.player, 'roi_round', 0.0), 4),
            max_dd=round(getattr(self.player, 'max_dd_round', 0.0), 4),
            trades=int(getattr(self.player, 'trade_count_round', 0)),
            turnover=round(getattr(self.player, 'turnover_round', 0.0), 4),
            anchor_bp=round(getattr(self.player, 'anchor_dev_bp_round', 0.0), 1),
        )
        p.vars['last_round_features'] = features
        # ==============================================================================

        # Where Qualtrics must send them back (the next oTree page in sequence)
        return_url = self._url_next

        # Base Qualtrics link for the BETWEEN-ROUND block
        q_base = s.config.get('nudge_link_round')

        params = dict(
            PROLIFIC_PID=p.vars.get('PROLIFIC_PID', 'NA'),
            session=p.code,
            arm=arm,                                # <-- Qualtrics branches on this
            round=self.round_number,
            roi=features['roi'],
            max_dd=features['max_dd'],
            trades=features['trades'],
            turnover=features['turnover'],
            anchor_bp=features['anchor_bp'],
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
