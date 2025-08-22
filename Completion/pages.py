from otree.api import *
from urllib.parse import urlencode

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer): pass

class WrapUpRedirect(Page):
    def vars_for_template(self):
        p = self.participant
        s = self.session
        wrap_base = s.config.get('survey_link')  # final Qualtrics wrap-up link from settings
        params = dict(
            PROLIFIC_PID=p.vars.get('PROLIFIC_PID','NA'),
            session=p.code,
            arm=p.vars.get('arm','NA'),
        )
        q_url = f"{wrap_base}?{urlencode(params)}"
        return dict(q_url=q_url)

page_sequence = [WrapUpRedirect]
