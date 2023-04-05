from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

import datetime


class TriviaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]

        # Verify is joined
        if await self.verify_player():
            self.group_name = f'game_{self.game_id}'

            print(f'Conectado: {self.channel_name}')

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content=None):
        print(content)
        if content['action'] == 'start':
            await self.action_start(int(content['rounds']))
        elif content['action'] == 'question':
            await self.action_question(content['text'])
        elif content['action'] == 'answer':
            await self.action_answer(content['text'])

    async def game_message(self, event):
        message = event["message"]

        if 'userid' not in event or event['userid'] == self.scope['user'].id:
            await self.send_json(content=message)

    async def action_start(self, rounds=None):
        creator, is_open, player_count = await self.get_game_params()

        if self.scope['user'].id == creator.id:
            if player_count > 1:
                if is_open:
                    if rounds is not None and rounds >= player_count:
                        players = await self.start_game(rounds)
                        await self.channel_layer.group_send(
                            self.group_name, {"type": "game_message", "message": {
                                'type': 'game_started',
                                'rounds': rounds,
                                'players': players,
                            }}
                        )

                        round_number, nosy_id = await self.next_round()
                        await self.channel_layer.group_send(
                            self.group_name, {"type": "game_message", "message": {
                                'type': 'round_started',
                                'round_number': round_number,
                                'nosy_id': nosy_id,
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

    async def action_question(self, q_text):
        creator, is_open, player_count = await self.get_game_params()

        if not is_open:
            round, nosy = await self.get_current_round()
            if self.scope['user'].id == nosy.id:
                if round.question_arrived is None:
                    await self.save_question(q_text)
                    await self.channel_layer.group_send(
                        self.group_name, {"type": "game_message", "message": {
                            'type': 'round_question',
                            'question': q_text,
                        }}
                    )
                else:
                    await self.send_json(content={
                        'type': 'error',
                        'message': 'Ya se entregó la pregunta de esta ronda'
                    })
            else:
                await self.send_json(content={
                    'type': 'error',
                    'message': 'Solo el pregunton puede enviar la pregunta de la ronda'
                })
        else:
            await self.send_json(content={
                'type': 'error',
                'message': 'El juego aun no comienza'
            })

    async def action_answer(self, a_text):
        creator, is_open, player_count = await self.get_game_params()

        if not is_open:
            round, nosy = await self.get_current_round()

            if round.answer_ended is None:
                move = await self.save_answer(a_text)

                if move is not None:
                    if self.scope['user'].id != nosy.id:
                        await self.channel_layer.group_send(
                            self.group_name, {"type": "game_message", 'userid': nosy.id, "message": {
                                'type': 'round_answer',
                                'answer': a_text,
                                'userid': self.scope['user'].id,
                            }}
                        )
                else:
                    await self.send_json(content={
                        'type': 'error',
                        'message': 'No se puede cambiar la respuesta previamente enviada'
                    })
            else:
                await self.send_json(content={
                    'type': 'error',
                    'message': 'Ya no se aceptan respuestas en esta ronda'
                })
        else:
            await self.send_json(content={
                'type': 'error',
                'message': 'El juego aun no comienza'
            })

    @database_sync_to_async
    def verify_player(self):
        if self.scope['user'].is_anonymous:
            return False
        else:
            return self.scope['user'].games.filter(id=self.game_id).exists()

    @database_sync_to_async
    def get_game_params(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        return game.creator, game.is_open, game.players_count

    @database_sync_to_async
    def start_game(self, rounds):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        game.started = datetime.datetime.now()
        game.rounds_number = rounds
        game.save()

        return [{'username': p.username, 'userid': p.id} for p in game.players.all()]

    @database_sync_to_async
    def next_round(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        if game.next_round():
            return game.rounds.count(), game.current_round.nosy.id
        else:
            return False

    @database_sync_to_async
    def get_current_round(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        if round is None:
            return None
        else:
            return round, round.nosy

    @database_sync_to_async
    def save_question(self, q_text):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        round.question = q_text
        round.question_arrived = datetime.datetime.now()
        round.save()

    @database_sync_to_async
    def save_answer(self, a_text):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        move = round.add_answer(self.scope['user'], a_text)

        return move
