from django.contrib import admin

from trivia_api.models import Game, Round, Move, Qualification, Fault


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'creator', 'players_count', 'is_open', 'started', 'rounds_number', 'remaining_rounds')
    list_filter = ('creator', 'started', 'ended')


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('game', 'started', 'nosy', 'question', 'missing_players_count', 'missing_evaluations_count')
    list_filter = ('game', 'nosy')

    @admin.display(description="missing_players")
    def missing_players_count(self, obj):
        return len(obj.missing_players)

    @admin.display(description="missing_evaluations")
    def missing_evaluations_count(self, obj):
        return len(obj.missing_evaluations)


@admin.register(Move)
class MoveAdmin(admin.ModelAdmin):
    list_display = ('round', 'created', 'player', 'evaluation', 'auto_evaluation')
    list_filter = ('evaluation', 'auto_evaluation')


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('move', 'player', 'sent')
    list_filter = ('is_correct',)


@admin.register(Fault)
class FaultAdmin(admin.ModelAdmin):
    list_display = ('round', 'player', 'category')
    list_filter = ('player', 'category')
