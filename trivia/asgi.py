import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trivia.settings')

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from trivia.routing import ws_urlpatterns
from trivia_api.middlewares import JwtAuthMiddleware


application = ProtocolTypeRouter({
    'http':  get_asgi_application(),
    'websocket': JwtAuthMiddleware(URLRouter(ws_urlpatterns))
})

