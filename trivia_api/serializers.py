from rest_framework import serializers

from trivia_api.models import Game


class GameSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    created = serializers.DateTimeField(read_only=True)
    player_count = serializers.IntegerField(
        source='players.count', read_only=True
    )

    class Meta:
        model = Game
        fields = '__all__'

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
