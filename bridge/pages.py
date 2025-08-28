from otree.api import *
import os, requests

class Intro(Page):
    def vars_for_template(player: Player):
        return dict()

    def before_next_page(player: Player, timeout_happened):
        # read pid from room join URL
        pid = player.participant.label
        if not pid:
            # fallback: accept ?pid=... if not using room join
            req = player.get_http_request()
            pid = req.GET.get('pid')

        player.pid = pid or ''
        pvars = player.participant.vars
        pvars['pid'] = player.pid

        # lookup assignment server-side
        cfg = player.session.config
        base = cfg.get('ASSIGN_API_BASE')
        token = cfg.get('OTREE_ASSIGN_READ_TOKEN', '')
        r = requests.get(
            f"{base}/assignment/{player.pid}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        r.raise_for_status()
        cond = int(r.json().get('cond', 0))
        player.cond = cond
        pvars['cond'] = cond

class LaunchZTS(Page):
    def vars_for_template(player: Player):
        cfg = player.session.config
        return dict(
            zts_host=cfg.get('ZTS_HOST'),
            pid=player.participant.vars.get('pid'),
            cond=player.participant.vars.get('cond'),
        )

page_sequence = [Intro, LaunchZTS]
