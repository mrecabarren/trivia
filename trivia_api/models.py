from django.contrib.auth.models import User
from django.db import models

import datetime
import random


class OpenGamesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(started__isnull=True)


class Game(models.Model):
    name = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, blank=True)

    question_time = models.IntegerField(default=90)
    answer_time = models.IntegerField(default=90)
    rounds_number = models.IntegerField(null=True, blank=True, default=None)

    players = models.ManyToManyField(
        User, blank=True, related_name='games'
    )

    started = models.DateTimeField(null=True, blank=True, default=None)
    ended = models.DateTimeField(null=True, blank=True, default=None)

    # managers
    objects = models.Manager()
    open = OpenGamesManager()

    def __str__(self):
        return f'{self.name} [{self.creator}]'

    @property
    def players_count(self):
        return self.players.count()

    @property
    def is_open(self):
        return self.started is None

    @property
    def remaining_rounds(self):
        return self.rounds_number - self.rounds.count() if self.rounds_number is not None else None

    @property
    def current_round(self):
        if self.rounds.count() > 0:
            return self.rounds.latest('started')
        else:
            return None

    def next_round(self):
        if self.remaining_rounds > 0:
            Round.objects.create(game=self,
                                 nosy=self.next_nosy(),
                                 started=datetime.datetime.now())
            return True
        else:
            return False

    def next_nosy(self):
        # random without repeat
        if self.rounds.count() <= self.players_count:
            p_ready = [r.noisy.id for r in self.rounds.all()]
            p_avalable = [p for p in self.players.all() if p.id not in p_ready]
            return random.choice(p_avalable)
        # TODO: worse score, but not repeat
        else:
            return self.creator


class Round(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='rounds')

    nosy = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField(null=True, blank=True, default=None)

    started = models.DateTimeField(auto_now_add=True, blank=True)
    question_arrived = models.DateTimeField(null=True, blank=True, default=None)
    answer_ended = models.DateTimeField(null=True, blank=True, default=None)
    ended = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.started} [{self.game}]'


class Move(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='moves')
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.TextField(null=True, blank=True, default=None)
    evaluation = models.IntegerField(null=True, blank=True, default=None)

    created = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return f'{self.player} [{self.round}]'


class Qualification(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qualifications')
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='qualifications')
    is_correct = models.BooleanField(null=True, blank=True, default=None)

    created = models.DateTimeField(auto_now_add=True, blank=True)
    sent = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.player} [{self.move}] -- {self.is_correct}'


class Fault(models.Model):
    FAULT_CATEGORIES = [
        ('QT', 'QUESTION TIME'),
        ('AT', 'ANSWER TIME'),
        ('ET', 'EVALUATION TIME'),
        ('QT', 'QUALIFICATION TIME'),
        ('FF', 'FOCUS'),
    ]

    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='faults')
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='faults')
    category = models.CharField(max_length=2, choices=FAULT_CATEGORIES)
    description = models.TextField()

    def __str__(self):
        return f'{self.player} [{self.round}]'
