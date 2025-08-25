from django.shortcuts import render


def login_view(request):
    context = {"name": "World"}
    return render(request, "accounts/index.html", context)
