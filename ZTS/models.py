import json
import random
import re
from otree.api import *
c = cu
from otree.api import (
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
    Currency as c,
    currency_range,
)

author = 'Jason Friedman, Student Helper COG, ETHZ'

doc = """
Trading App of the Zurich Trading Simulator (ZTS).
A web-based behaviour experiment in the form of a trading game, 
designed by the Chair of Cognitive Science - ETH Zurich.
"""

class Constants(BaseConstants):
    name_in_url = 'zts'
    players_per_group = None
    num_rounds = 20  # Actual num_rounds is specified in session config, by the length of the list 'timeseries_filename'!


class Subsession(BaseSubsession):

    def creating_session(self):
        """
        Called before each creation of a ZTS subsession.
        - Sets effective number of rounds from timeseries_filename list.
        - Draws a random payoff round (excluding training round if present).
        """
        if self.round_number == 1:
            self.session.num_rounds = len(json.loads(self.session.config['timeseries_filename']))

            for player in self.get_players():
                first_round = 1
                if self.session.config['training_round']:
                    first_round = 2

                if first_round > self.session.num_rounds:
                    raise ValueError('Num rounds cannot be smaller than 1 (or 2 if there is a training session)!')

                player.participant.vars['round_to_pay'] = random.randint(first_round, self.session.num_rounds)

    def get_config_multivalue(self, value_name):
        """
        Config values may be a list (per round) or a single value.
        Return the value for the current round.
        """
        parsed_value = json.loads(self.session.config[value_name])
        if isinstance(parsed_value, list):
            assert len(parsed_value) >= self.session.num_rounds, value_name + ' contains less entries than effective rounds!'
            return parsed_value[self.round_number - 1]
        else:
            return parsed_value

    def get_timeseries_values(self):
        """
        Read this round's timeseries file and parse lists of values.

        :return: (asset_name, prices, news_list_or_empty_str_list)
        """
        filename = self.get_config_multivalue('timeseries_filename')
        asset = filename.strip('.csv')
        path = self.session.config['timeseries_filepath'] + filename
        rows = read_csv(path, TimeSeriesFile)
        prices = [dic['price'] for dic in rows]
        if 'news' in rows[0].keys():
            news = [dic['news'] if dic['news'] else '' for dic in rows]
        else:
            news = '' * len(prices)
        return asset, prices, news


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    cash = models.FloatField(initial=1000000)
    shares = models.FloatField(initial=0)
    share_value = models.FloatField(initial=0)
    portfolio_value = models.FloatField(initial=0)
    pandl = models.FloatField(initial=0)

    # Optional: persist simple round-start value if you want it saved as a field
    portfolio_value_start = models.FloatField(initial=0)

    # Helper to init/reset per-round logs safely
    def _ensure_round_logs(self, reset: bool = False):
        pvars = self.participant.vars
        if reset or ('pv_series_round' not in pvars):
            pvars['pv_series_round'] = []
        if reset or ('trades_log_round' not in pvars):
            pvars['trades_log_round'] = []
        if reset or ('anchors_round' not in pvars):
            pvars['anchors_round'] = []

    def _try_append_anchor_from_payload(self, payload: dict):
        """
        Try to capture a numeric anchor from common payload fields.
        Looks for: 'anchor', 'news_anchor', or parses first number from 'news'.
        """
        pvars = self.participant.vars
        self._ensure_round_logs()  # ensure containers exist
        anchor_val = None

        # direct numeric fields
        for key in ('anchor', 'news_anchor'):
            if key in payload:
                try:
                    val = float(payload.get(key))
                    if val > 0:
                        anchor_val = val
                        break
                except Exception:
                    pass

        # parse from news text if not found yet
        if anchor_val is None and 'news' in payload:
            try:
                text = payload.get('news', '')
                if isinstance(text, str) and text:
                    m = re.search(r'(-?\d+(?:\.\d+)?)', text.replace(',', ''))
                    if m:
                        val = float(m.group(1))
                        if val > 0:
                            anchor_val = val
            except Exception:
                pass

        if anchor_val is not None:
            try:
                pvars['anchors_round'].append(anchor_val)
            except Exception:
                pass

    def live_trading_report(self, payload):
        """
        Accepts the trading reports from the front end and
        stores them in the database; also logs per-round series for metrics.
        :param payload: trading report dict
        """
        # Ensure per-round logs exist
        self._ensure_round_logs()

        # Copy primary state from payload (original behavior)
        self.cash = float(payload['cash'])
        self.shares = int(payload['owned_shares'])
        self.share_value = float(payload['share_value'])
        self.portfolio_value = float(payload['portfolio_value'])
        self.pandl = float(payload['pandl'])

        # If this is the first message of the round (action 'Start'), reset logs and set starting PV
        if payload.get('action') == 'Start':
            self._ensure_round_logs(reset=True)
            # record round start portfolio value
            try:
                self.portfolio_value_start = float(self.portfolio_value)
                self.participant.vars['pv_series_round'].append(float(self.portfolio_value_start))
            except Exception:
                pass

        # Append current portfolio value to the series on every message
        try:
            if self.portfolio_value is not None:
                self.participant.vars['pv_series_round'].append(float(self.portfolio_value))
        except Exception:
            pass

        # Try to capture anchors if present (optional)
        self._try_append_anchor_from_payload(payload)

        # Persist action to ExtraModel (original behavior)
        TradingAction.create(
            player=self,
            action=payload['action'],
            quantity=payload['quantity'],
            time=payload['time'],
            price_per_share=payload['price_per_share'],
            cash=payload['cash'],
            owned_shares=payload['owned_shares'],
            share_value=payload['share_value'],
            portfolio_value=payload['portfolio_value'],
            cur_day=payload['cur_day'],
            asset=payload['asset'],
            roi=payload['roi_percent']
        )

        # If an actual trade occurred, append minimal trade log (qty/price/side)
        try:
            side = payload.get('action')
            if side in ('Buy', 'Sell'):
                qty = float(payload.get('quantity', 0.0))
                px = float(payload.get('price_per_share', 0.0))
                if abs(qty) > 0 and px > 0:
                    self.participant.vars['trades_log_round'].append({
                        'qty': qty,
                        'price': px,
                        'side': side,
                        'ts': payload.get('time', self.round_number),
                    })
        except Exception:
            pass

        # End of round -> set payoff (original behavior)
        if payload['action'] == 'End':
            self.set_payoff()

    def set_payoff(self):
        """
        Set the player's payoff for the current round to the total portfolio value.
        If we want the participant's final payoff to be chosen randomly
        from all rounds (random_round_payoff), subtract current payoff
        from participant.payoff if we are not in round_to_pay.
        Also exclude training round from payoff.
        """
        self.payoff = 0
        self.payoff = self.portfolio_value
        random_payoff = self.session.config['random_round_payoff']
        training_round = self.session.config['training_round']
        if random_payoff and self.round_number != self.participant.vars['round_to_pay']:
            self.participant.payoff -= self.payoff
        elif training_round and self.round_number == 1:
            self.participant.payoff -= self.payoff


class TradingAction(ExtraModel):
    """
    Extra database model storing all transactions. Each transaction is
    linked to the player who executed it.
    """
    ACTIONS = [
        ('Buy', 'Buy'),
        ('Sell', 'Sell'),
        ('Start', 'Start'),
        ('End', 'End'),
    ]

    player = models.Link(Player)
    action = models.CharField(choices=ACTIONS, max_length=10)
    quantity = models.FloatField(initial=0.0)
    time = models.StringField()
    price_per_share = models.FloatField()
    cash = models.FloatField()
    owned_shares = models.FloatField()
    share_value = models.FloatField()
    portfolio_value = models.FloatField()
    cur_day = models.IntegerField()
    asset = models.CharField(blank=True, max_length=100)
    roi = models.FloatField()


class TimeSeriesFile(ExtraModel):
    date = models.StringField()
    price = models.FloatField()
    news = models.StringField()


def custom_export(players):
    """
    Custom export with detailed trading actions.
    NOTE: exports actions from the whole DB; add filtering if you need per-session only.
    """
    # header row
    yield ['session', 'round_nr', 'participant', 'action', 'quantity', 'price_per_share', 'cash',
           'owned_shares', 'share_value', 'portfolio_value', 'cur_day', 'asset', 'roi']
    # data content
    for p in players:
        for ta in TradingAction.filter(player=p):
            yield [p.session.code, p.subsession.round_number, p.participant.code, ta.action, ta.quantity,
                   ta.price_per_share, ta.cash, ta.owned_shares, ta.share_value, ta.portfolio_value,
                   ta.cur_day, ta.asset, ta.roi]
