from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'bridge'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass

class Player(BasePlayer):
    pid  = models.StringField()
    cond = models.IntegerField(choices=[0,1], initial=0)
    round_index = models.IntegerField(initial=1)
