from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from trivia_api.models import Game
from trivia_api.serializers import GameSerializer, PlayerSerializer


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.open.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]

    @action(
        detail=True,
        methods=['post'],
    )
    def join_game(self, request, pk=None):
        game = self.get_object()

        if game.is_open:
            game.players.add(self.request.user)

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'game_{game.id}',
                {
                    'type': "game_message",
                    'message': {'type': 'player_joined',
                                'userid': self.request.user.id,
                                'username': self.request.user.username}
                }
            )

            return Response(
                data={
                    "message": "Te has unido correctamente al juego.",
                    "game_id": game.id,
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                data={
                    "message": "El juego ya comenzó, no permite inscripción.",
                    "game_id": game.id,
                },
                status=status.HTTP_423_LOCKED
            )

    @action(
        detail=True,
        methods=['post'],
    )
    def unjoin_game(self, request, pk=None):
        game = self.get_object()

        if game.is_open:
            if game.creator.id != self.request.user.id:
                if game.players.filter(id=self.request.user.id).exists():
                    game.players.remove(self.request.user)

                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f'game_{game.id}',
                        {
                            'type': "game_message",
                            'message': {'type': 'player_unjoined',
                                        'userid': self.request.user.id,
                                        'username': self.request.user.username}
                        }
                    )

                    return Response(
                        data={
                            "message": "Te has desvinculado correctamente del juego.",
                            "game_id": game.id,
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        data={
                            "message": "El usuario que se quiere desvincular no está inscrito en el juego.",
                            "game_id": game.id,
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    data={
                        "message": "El crador del juego no puede desvincularse.",
                        "game_id": game.id,
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                data={
                    "message": "El juego ya comenzó, no permite desvinculare.",
                    "game_id": game.id,
                },
                status=status.HTTP_423_LOCKED
            )

    @action(
        detail=True,
        methods=['post'],
        queryset=Game.objects.all(),
    )
    def state(self, request, pk=None):
        game = self.get_object()
        c_round = game.current_round

        if not game.is_open:
            game_state = {
                'rounds': game.rounds_number,
                'current_round': game.current_round_idx,
                'round': {
                    'nosy': c_round.nosy.id if c_round.nosy is not None else None,
                    'question': c_round.question,
                    'phase': c_round.current_phase,
                } if c_round is not None else None,
                'players': [
                    {'id': p.id, 'score': game.player_score(p.id), 'faults': game.player_faults(p.id)}
                    for p in game.players.all()
                ],
                'ended': game.ended,
            }
            return Response(
                data=game_state,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                data={
                    "message": "El juego aun no ha comenzado.",
                    "game_id": game.id,
                },
                status=status.HTTP_423_LOCKED
            )

    def perform_create(self, serializer):
        instance = serializer.save(creator=self.request.user)
        instance.players.add(self.request.user)

    def perform_destroy(self, instance):
        if not instance.creator.id == self.request.user.id:
            raise PermissionDenied("You are not allowed to perform this action.")

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'game_{instance.id}',
            {
                'type': "game_message",
                'message': {'type': 'game_deleted',
                            'game': instance.id,
                            }
            }
        )
        instance.delete()


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PlayerSerializer(request.user)

        return Response(serializer.data)
