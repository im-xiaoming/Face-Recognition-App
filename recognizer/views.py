from django.shortcuts import render

# Create your views here.
def recognizer(request):
    return render(request, 'recognizer/recognition.html')