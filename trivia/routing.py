from django.urls import path

from trivia_api.consumers import TriviaConsumer

ws_urlpatterns = [
    path("ws/trivia/<int:game_id>/", TriviaConsumer.as_asgi()),
]