from uuid import uuid4

from django.contrib.auth.models import AnonymousUser


SERVER_SESSION_TOKEN = uuid4().hex
SERVER_SESSION_KEY = '_server_session_token'


class LogoutOnServerRestartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            session_token = request.session.get(SERVER_SESSION_KEY)
            if session_token != SERVER_SESSION_TOKEN:
                request.session.flush()
                request.user = AnonymousUser()
            else:
                request.session[SERVER_SESSION_KEY] = SERVER_SESSION_TOKEN

        response = self.get_response(request)

        if getattr(request, 'user', None) and request.user.is_authenticated:
            request.session[SERVER_SESSION_KEY] = SERVER_SESSION_TOKEN

        return response
