from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

# Create your views here.
def home(request):
    return render(request, 'home/home.html')


@require_POST
def auto_logout(request):
    was_authenticated = request.user.is_authenticated
    if was_authenticated:
        logout(request)

    return JsonResponse({
        'authenticated': False,
        'logged_out': was_authenticated,
    })
