from otree.api import *
from django.db import models as djm

class C(BaseConstants):
    NAME_IN_URL = 'bridge'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass

class Player(BasePlayer):
    pid  = models.StringField()
    cond = models.IntegerField(choices=[0, 1], initial=0)
    round_index = models.IntegerField(initial=1)

# Local assignment store so Qualtrics can POST directly into oTree
class Assignment(djm.Model):
    pid = djm.CharField(primary_key=True, max_length=128)
    cond = djm.PositiveSmallIntegerField()
    assigned_at = djm.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assignments'
