from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

import datetime

from trivia_api.models import Game


class TriviaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]

        print(f"TriviaConsumer - {self.game_id} - {self.scope['user']}")

        # Verify is joined
        if await self.verify_player():
            self.group_name = f'game_{self.game_id}'

            print("Conectado")

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content=None):
        print(content)
        if content['action'] == 'start':
            await self.action_start(int(content['rounds']))

    async def game_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send_json(content=message)

    async def action_start(self, rounds=None):
        creator, is_open, player_count = await self.get_game_params()
        if self.scope['user'] == creator:
            if player_count > 1:
                if is_open:
                    if rounds is not None and rounds >= player_count:
                        await self.start_game(rounds)
                        await self.channel_layer.group_send(
                            self.group_name, {"type": "game_message", "message": {
                                'type': 'game_started',
                                'rounds': rounds,
                            }}
                        )
                    else:
                        await self.send_json(content={
                            'type': 'error',
                            'message': 'El número de rondas debe ser mayor o igual al número de jugadores'
                        })
                else:
                    await self.send_json(content={
                        'type': 'error',
                        'message': 'La partida ya había sido iniciada'
                    })
            else:
                await self.send_json(content={
                    'type': 'error',
                    'message': 'Para iniciar la partida debe tener al menos 2 jugadores inscritos'
                })
        else:
            await self.send_json(content={
                'type': 'error',
                'message': 'La partida solo la puede iniciar quien la creó'
            })

    @database_sync_to_async
    def verify_player(self):
        if self.scope['user'].is_anonymous:
            return False
        else:
            return self.scope['user'].games.filter(id=self.game_id).exists()

    @database_sync_to_async
    def get_game_params(self):
        game = Game.objects.get(id=self.game_id)
        return game.creator, game.is_open, game.players_count

    @database_sync_to_async
    def start_game(self, rounds):
        game = Game.objects.get(id=self.game_id)
        game.started = datetime.datetime.now()
        game.rounds_number = rounds
        game.save()
