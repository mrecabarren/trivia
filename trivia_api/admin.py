from django.contrib import admin

from trivia_api.models import Game, Round, Move, Qualification, Fault, ActionError


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'creator', 'players_count', 'is_open', 'started', 'ended',
                    'rounds_number', 'remaining_rounds', 'disqualified_players_count')
    list_filter = ('creator', 'started', 'ended')

    @admin.display(description="disqualified_players")
    def disqualified_players_count(self, obj):
        return len(obj.disqualified_players)


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('game', 'index', 'started', 'nosy', 'nosy_score', 'question', 'missing_players_count',
                    'missing_evaluations_count', 'ended')
    list_filter = ('game', 'nosy')

    @admin.display(description="missing_players")
    def missing_players_count(self, obj):
        return len(obj.missing_players)

    @admin.display(description="missing_evaluations")
    def missing_evaluations_count(self, obj):
        return len(obj.missing_evaluations)


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('game', 'round_index', 'player', 'created', 'evaluation', 'auto_evaluation')
    list_filter = ('evaluation', 'auto_evaluation')

    @admin.display(description="game")
    def game(self, obj):
        return obj.round.game

    @admin.display(description="round_index")
    def round_index(self, obj):
        return obj.round.index


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('game', 'round_index', 'player', 'move_player', 'qualified', 'is_correct')
    list_filter = ('move__round__game', 'is_correct', 'player')

    @admin.display(description="move_player")
    def move_player(self, obj):
        return obj.move.player

    @admin.display(description="game")
    def game(self, obj):
        return obj.move.round.game

    @admin.display(description="round_index")
    def round_index(self, obj):
        return obj.move.round.index


@admin.register(Fault)
class FaultAdmin(admin.ModelAdmin):
    list_display = ('game', 'round_index', 'player', 'category', 'fault_value')
    list_filter = ('player', 'category', 'round__game')

    @admin.display(description="game")
    def game(self, obj):
        return obj.round.game

    @admin.display(description="round_index")
    def round_index(self, obj):
        return obj.round.index


@admin.register(ActionError)
class ActionErrorAdmin(admin.ModelAdmin):
    list_display = ('game', 'round_index', 'player', 'action', 'error_message')
    list_filter = ('player', 'action', 'round__game')

    @admin.display(description="game")
    def game(self, obj):
        return obj.round.game if obj.round is not None else None

    @admin.display(description="round_index")
    def round_index(self, obj):
        return obj.round.index if obj.round is not None else None
