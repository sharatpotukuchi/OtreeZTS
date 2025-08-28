from otree.api import *
import requests, os
from urllib.parse import urlencode

class Intro(Page):
    def before_next_page(player: Player, timeout_happened):
        req = player.get_http_request()
        # PID from room join (participant_label). Fallback to ?pid=
        pid = player.participant.label or req.GET.get('pid')
        player.pid = pid or 'NA'
        player.participant.vars['PROLIFIC_PID'] = player.pid

        # Round index from ?round= (default 1)
        rnd = req.GET.get('round', '1')
        try:
            player.round_index = int(rnd)
        except:
            player.round_index = 1
        player.participant.vars['round'] = player.round_index

        # Securely look up condition
        cfg = player.session.config
        base  = cfg.get('ASSIGN_API_BASE')
        token = cfg.get('OTREE_ASSIGN_READ_TOKEN', '')
        r = requests.get(f"{base}/assignment/{player.pid}",
                         headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r.raise_for_status()
        cond = int(r.json().get('cond', 0))
        player.cond = cond
        pv = player.participant.vars
        pv['cond'] = cond
        pv['arm']  = cond  # (if you still use 'arm' in Qualtrics)

class LaunchZTS(Page):
    def vars_for_template(player: Player):
        cfg = player.session.config
        return dict(
            zts_host = cfg.get('ZTS_HOST'),
            pid      = player.pid,
            cond     = player.cond,
            rnd      = player.round_index,
        )

class ToQualtrics(Page):
    def vars_for_template(player: Player):
        # Between-round Qualtrics URL with params
        cfg = player.session.config
        q_base = cfg.get('nudge_link_round')  # Qualtrics “between-round” survey
        params = dict(
            PROLIFIC_PID = player.pid,
            session      = player.participant.code,
            cond         = player.cond,
            round        = player.round_index,
        )
        return dict(q_url=f"{q_base}?{urlencode(params)}")

page_sequence = [Intro, LaunchZTS, ToQualtrics]
