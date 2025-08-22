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
        return dict(
            is_training_round=is_training_round,
        )


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
            trading_button_values=self.subsession.get_config_multivalue('trading_button_values')
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


# --- NEW: Between-round pages ---

class BetweenRoundRedirect(Page):
    """
    Shown BETWEEN rounds for the TREATMENT arm.
    Redirects to Qualtrics 'nudge' block with Embedded Data (features),
    then Qualtrics sends the user back to the NEXT ZTS page via ?return_to=...
    """
    timeout_seconds = 2  # brief pause before meta-refresh (template)

    def is_displayed(self):
        # Only between rounds (not after the last) AND only if we have a nudge link AND participant is treatment
        not_last_round = self.round_number < self.session.num_rounds
        is_treatment = (self.participant.vars.get('arm') == 'treatment')
        has_link = bool(self.session.config.get('nudge_link_round'))
        return not_last_round and is_treatment and has_link

    def vars_for_template(self):
        p = self.participant
        s = self.session

        # ====== TODO: plug in your real feature computations per round ======
        # These placeholders read values that you will compute & set on `self.player`
        # (or compute here from logs when you're ready).
        features = dict(
            roi=round(getattr(self.player, 'roi_round', 0.0), 4),
            max_dd=round(getattr(self.player, 'max_dd_round', 0.0), 4),
            trades=int(getattr(self.player, 'trade_count_round', 0)),
            turnover=round(getattr(self.player, 'turnover_round', 0.0), 4),
            anchor_bp=round(getattr(self.player, 'anchor_dev_bp_round', 0.0), 1),
        )
        p.vars['last_round_features'] = features
        # ================================================================

        # URL where Qualtrics should return the participant after the nudge block
        # NOTE: _url_next is the URL oTree would send the user to if they clicked "Next" here.
        return_url = self._url_next

        # Build Qualtrics nudge URL with Embedded Data
        nudge_base = s.config.get('nudge_link_round')
        params = dict(
            PROLIFIC_PID=p.vars.get('PROLIFIC_PID', 'NA'),
            session=p.code,
            round=self.round_number,
            roi=features['roi'],
            max_dd=features['max_dd'],
            trades=features['trades'],
            turnover=features['turnover'],
            anchor_bp=features['anchor_bp'],
            return_to=return_url,  # Qualtrics end-of-block should redirect to this
        )
        q_url = f"{nudge_base}?{urlencode(params)}"
        return dict(q_url=q_url)


class BetweenRoundPause(Page):
    """
    Shown BETWEEN rounds for the CONTROL arm to match timing/experience.
    """
    timeout_seconds = 2

    def is_displayed(self):
        not_last_round = self.round_number < self.session.num_rounds
        is_control = (self.participant.vars.get('arm') == 'control')
        return not_last_round and is_control

    def vars_for_template(self):
        return dict()


# Ensure the between-round pages are evaluated AFTER ResultsPage and BEFORE the next Start/Trading round.
page_sequence = [
    InstructionPage,
    StartPage,
    TradingPage,
    ResultsPage,
    BetweenRoundRedirect,  # (treatment only)
    BetweenRoundPause,     # (control only)
]
