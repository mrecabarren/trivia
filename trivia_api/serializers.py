from django.contrib.auth.models import User

from rest_framework import serializers

from trivia_api.models import Game


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class PlayerSerializer(serializers.ModelSerializer):
    games_created = serializers.SerializerMethodField()
    games_joined = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'games_created', 'games_joined']

    def get_games_created(self, obj):
        return GameLightSerializer(
            Game.objects.filter(creator=obj).all(),
            many=True
        ).data

    def get_games_joined(self, obj):
        return GameLightSerializer(
            Game.objects.filter(players__id=obj.id).all(),
            many=True
        ).data


class GameSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    player_count = serializers.IntegerField(
        source='players.count', read_only=True
    )
    players = UserSerializer(read_only=True, many=True)
    i_can_start = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = '__all__'

    def get_i_can_start(self, obj):
        if obj.creator.id == self.context['request'].user.id:
            return True
        return False

    def validate_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("El nombre de un juego debe tener al menos 3 caracteres")
        return value

    def validate_question_time(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError(
                'El valor dado para QUESTION TIME debe ser numérico')
        else:
            question_time = int(value)
            if question_time not in [60, 90, 120]:
                raise serializers.ValidationError(
                    'El valor para QUESTION TIME no es uno de los permitidos')
        return value

    def validate_answer_time(self, value):
        if not isinstance(value, int):
            raise serializers.ValidationError(
                'El valor dado para ANSWER TIME debe ser numérico')
        else:
            answer_time = int(value)
            if answer_time not in [60, 90, 120]:
                raise serializers.ValidationError(
                    'El valor para ANSWER TIME no es uno de los permitidos')
        return value


class GameLightSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    player_count = serializers.IntegerField(
        source='players.count', read_only=True
    )

    class Meta:
        model = Game
        fields = ['id', 'name', 'creator', 'created', 'player_count', 'question_time', 'answer_time', 'rounds_number',
                  'started', 'ended']

