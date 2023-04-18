import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

import datetime


class TriviaConsumer(AsyncJsonWebsocketConsumer):
    DELTA_TIME = 2
    QUALIFY_TIME = 90

    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]

        # Verify is joined
        if await self.verify_player():
            self.group_name = f'game_{self.game_id}'

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content=None):
        print(f'{self.scope["user"]} -> {content}`')
        if content['action'] == 'start':
            await self.action_start(int(content['rounds']))
        elif content['action'] == 'question':
            await self.action_question(content['text'])
        elif content['action'] == 'answer':
            await self.action_answer(content['text'])
        elif content['action'] == 'qualify':
            await self.action_qualify(int(content['userid']), int(content['grade']))

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
                        await self.start_round_message(round_number, nosy_id)
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
                    self.answer_timer_task = asyncio.create_task(self.round_answer_timer())
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

            if round.question_arrived is not None:
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
                    'message': 'Aun no está la pregunta de la ronda'
                })
        else:
            await self.send_json(content={
                'type': 'error',
                'message': 'El juego aun no comienza'
            })

    async def action_qualify(self, userid, grade):
        creator, is_open, player_count = await self.get_game_params()

        if not is_open:
            round, nosy = await self.get_current_round()
            if self.scope['user'].id == nosy.id:
                if round.qualify_ended is None:
                    status = await self.save_answer_evaluation(userid, grade)

                    if not status:
                        await self.send_json(content={
                            'type': 'error',
                            'message': 'Este usuario no ha enviado una respuesta para ser evaluada'
                        })
                else:
                    await self.send_json(content={
                        'type': 'error',
                        'message': 'Ya no se aceptan calificaciones'
                    })
            else:
                await self.send_json(content={
                    'type': 'error',
                    'message': 'Solo el pregunton puede calificar las respuestas'
                })
        else:
            await self.send_json(content={
                'type': 'error',
                'message': 'El juego aun no comienza'
            })

    async def start_round_message(self, round_number, nosy_id):
        await self.channel_layer.group_send(
            self.group_name, {"type": "game_message", "message": {
                'type': 'round_started',
                'round_number': round_number,
                'nosy_id': nosy_id,
            }}
        )
        self.question_timer_task = asyncio.create_task(self.round_question_timer())

    @database_sync_to_async
    def verify_player(self):
        if self.scope['user'].is_anonymous:
            return False
        else:
            return self.scope['user'].games.filter(id=self.game_id).exists()

    @database_sync_to_async
    def get_game_base(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        return game

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

    @database_sync_to_async
    def restart_round(self):
        from trivia_api.models import Game
        game = Game.objects.get(id=self.game_id)

        game.restart_round()

        return game.rounds.count(), game.current_round.nosy

    @database_sync_to_async
    def answer_ended(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        round.answer_ended = datetime.datetime.now()
        round.save()

    @database_sync_to_async
    def qualify_ended(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        round.qualify_ended = datetime.datetime.now()
        round.save()

    @database_sync_to_async
    def save_answer_evaluation(self, userid, grade):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        status = round.add_answer_evaluation(userid, grade)

        return status

    @database_sync_to_async
    def get_players_without_move(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        return round.missing_players

    @database_sync_to_async
    def get_missing_evaluations(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        return round.missing_evaluations

    @database_sync_to_async
    def close_evaluations(self):
        from trivia_api.models import Game

        game = Game.objects.get(id=self.game_id)
        round = game.current_round
        round.close_evaluations()

    async def round_question_timer(self):
        game = await self.get_game_base()

        await asyncio.sleep(game.question_time + self.DELTA_TIME)
        c_round, nosy = await self.get_current_round()

        if c_round.question is None:
            # TODO: falta del nosy
            await self.channel_layer.group_send(
                self.group_name, {"type": "game_message", "message": {
                    'type': 'question_time_ended',
                }}
            )
            round_number, nosy = await self.restart_round()

            await self.start_round_message(round_number, nosy.id)

    async def round_answer_timer(self):
        game = await self.get_game_base()

        print(f'round_answer_timer starts: {game.answer_time + self.DELTA_TIME}')

        await asyncio.sleep(game.answer_time + self.DELTA_TIME)

        await self.channel_layer.group_send(
            self.group_name, {"type": "game_message", "message": {
                'type': 'answer_time_ended',
            }}
        )

        await self.answer_ended()

        missing_players = await self.get_players_without_move()

        print(f'round_answer_timer missing_players: {missing_players}')

        for p in missing_players:
            # TODO: falta del jugador
            pass

        await self.round_qualify_timer()

    async def round_qualify_timer(self):
        missing_evaluations = await self.get_missing_evaluations()

        if len(missing_evaluations) > 0:
            print(f'round_qualify_timer starts: {self.QUALIFY_TIME + self.DELTA_TIME}')
            await asyncio.sleep(self.QUALIFY_TIME + self.DELTA_TIME)

            missing_evaluations = await self.get_missing_evaluations()
            if len(missing_evaluations) > 0:
                await self.channel_layer.group_send(
                    self.group_name, {"type": "game_message", "message": {
                        'type': 'qualify_timeout',
                    }}
                )
                await self.close_evaluations()
                await self.qualify_ended()
        else:
            await self.qualify_ended()


