from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware


@database_sync_to_async
def get_user(validated_token):
	from django.contrib.auth import get_user_model

	try:
		user = get_user_model().objects.get(id=validated_token["user_id"])
		# return get_user_model().objects.get(id=toke_id)
		return user
	except:
		from django.contrib.auth.models import AnonymousUser

		return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
	def __init__(self, inner):
		self.inner = inner

	async def __call__(self, scope, receive, send):
		from rest_framework_simplejwt.tokens import UntypedToken

		token = parse_qs(scope["query_string"].decode("utf8"))["token"][0]

		try:
			UntypedToken(token)
		except (InvalidToken, TokenError) as e:
			return None
		else:
			decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
			scope["user"] = await get_user(validated_token=decoded_data)

		return await super().__call__(scope, receive, send)
