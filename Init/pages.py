from otree.api import *
import random

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

class InitIDs(Page):
    def is_displayed(self):
        # only once, first app page
        return True

    def vars_for_template(self):
        p = self.participant
        req = self.request.GET
        # Capture Prolific IDs if present (or leave NA)
        p.label = req.get('PROLIFIC_PID', p.label or 'NA')
        p.vars['PROLIFIC_PID'] = req.get('PROLIFIC_PID','NA')
        p.vars['STUDY_ID'] = req.get('STUDY_ID','NA')
        p.vars['SESSION_ID'] = req.get('SESSION_ID','NA')

        # Randomise arm once: 'treatment' or 'control'
        if 'arm' not in p.vars:
            p.vars['arm'] = random.choice(['treatment', 'control'])
        return dict(arm=p.vars['arm'])

page_sequence = [InitIDs]
