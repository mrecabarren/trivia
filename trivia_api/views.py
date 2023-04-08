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

    def perform_create(self, serializer):
        instance = serializer.save(creator=self.request.user)
        instance.players.add(self.request.user)

    def perform_destroy(self, instance):
        if not instance.creator.id == self.request.user.id:
            raise PermissionDenied("You are not allowed to perform this action.")
        instance.delete()


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = PlayerSerializer(request.user)

        return Response(serializer.data)
