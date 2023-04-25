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
    def current_round_idx(self):
        return self.rounds.count()

    @property
    def current_round(self):
        if self.rounds.count() > 0:
            return self.rounds.latest('started')
        else:
            return None

    @property
    def active_players(self):
        # TODO: jugadores no descalificados
        return self.players

    def next_round(self):
        if self.remaining_rounds > 0:
            Round.objects.create(game=self,
                                 nosy=self.next_nosy(),
                                 started=datetime.datetime.now())
            return True
        else:
            return False

    def restart_round(self):
        c_round = self.current_round
        if c_round is not None:
            c_round.nosy = None
            c_round.save()

            c_round.started = datetime.datetime.now()
            c_round.nosy = self.next_nosy()
            c_round.save()

    def next_nosy(self):
        # random without repeat
        if self.rounds.count() <= self.players_count:
            p_ready = [r.nosy.id for r in self.rounds.all() if r.nosy is not None]
            p_available = [p for p in self.players.all() if p.id not in p_ready]

            return random.choice(p_available)
        # TODO: worse score, but not repeat
        else:
            return self.creator

    def player_score(self, p_id):
        answering = Move.objects.filter(
            round__game=self, player=p_id, evaluation__isnull=False
        ).aggregate(models.Sum('evaluation'))
        answering_score = answering['evaluation__sum'] if answering['evaluation__sum'] is not None else 0
        asking = sum([r.nosy_score if r.nosy_score is not None else 0 for r in self.rounds.filter(nosy=p_id).all()])

        return answering_score + asking

    def player_faults(self, p_id):
        return Fault.objects.filter(round__game=self, player=p_id).count()


class Round(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='rounds')

    nosy = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, default=None)
    question = models.TextField(null=True, blank=True, default=None)

    started = models.DateTimeField(auto_now_add=True, blank=True)
    question_arrived = models.DateTimeField(null=True, blank=True, default=None)
    answer_ended = models.DateTimeField(null=True, blank=True, default=None)
    qualify_ended = models.DateTimeField(null=True, blank=True, default=None)
    ended = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.started} [{self.game}]'

    @property
    def missing_players(self):
        move_players = [m.player.id for m in self.moves.all()]

        return [p for p in self.game.players.all() if p.id not in move_players]

    @property
    def missing_evaluations(self):
        return [m for m in self.moves.filter(evaluation__isnull=True).exclude(player=self.nosy).all()]

    @property
    def correct_answer(self):
        nosy_move = self.moves.filter(player=self.nosy).first()
        return nosy_move.answer if nosy_move is not None else None

    @property
    def qualifications(self):
        return Qualification.objects.filter(move__round=self).all()

    @property
    def current_phase(self):
        if not self.question_arrived:
            return 'question'
        elif not self.answer_ended:
            return 'answering'
        elif not self.qualify_ended:
            return 'qualifying'
        elif not self.ended:
            return 'evaluating'
        else:
            return 'ended'

    @property
    def nosy_score(self):
        if self.ended:
            negative = Qualification.objects.filter(move__round=self, is_correct=False).count()
            players = self.game.active_players.count()-1

            if (players-negative)/players >= 0.8:
                return 3
            elif (players-negative)/players >= 0.5:
                return 1
            return -2
        else:
            return None

    def add_answer(self, player, answer):
        if self.moves.filter(player=player).count() == 0:
            move = Move.objects.create(round=self,
                                       player=player,
                                       answer=answer)
            return move
        else:
            return None

    def add_answer_evaluation(self, player, grade):
        move = self.moves.filter(player=player).first()
        if move is not None:
            move.evaluation = grade
            move.evaluated = datetime.datetime.now()
            move.save()
            return True

        return False

    def close_evaluations(self):
        for m in self.missing_evaluations:
            m.auto_grade()

    def create_qualifications(self):
        if self.qualifications.count() == 0:
            valid_moves = list(self.moves.exclude(player=self.nosy).order_by('created'))
            next_move = 0
            for p in self.game.active_players.exclude(id=self.nosy.id).all():
                if valid_moves[next_move].player.id == p.id:
                    valid_moves[next_move], valid_moves[(next_move+1) % len(valid_moves)] = valid_moves[(next_move+1) % len(valid_moves)], valid_moves[next_move]
                p_move = valid_moves[next_move]
                Qualification.objects.create(player=p,
                                             move=p_move)
                next_move = (next_move+1) % len(valid_moves)

    def get_qualification(self, playerid):
        return Qualification.objects.filter(player__id=playerid, move__round=self).first()


class Move(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='moves')
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.TextField(null=True, blank=True, default=None)
    evaluation = models.IntegerField(null=True, blank=True, default=None)
    auto_evaluation = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True, blank=True)
    evaluated = models.DateTimeField(null=True, blank=True, default=None)

    def __str__(self):
        return f'{self.player} [{self.round}]'

    def auto_grade(self):
        self.evaluation = 2
        self.auto_evaluation = True
        self.evaluated = datetime.datetime.now()

        self.save()


class Qualification(models.Model):
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qualifications')
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name='qualifications')
    is_correct = models.BooleanField(null=True, blank=True, default=None)

    created = models.DateTimeField(auto_now_add=True, blank=True)
    qualified = models.DateTimeField(null=True, blank=True, default=None)

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
