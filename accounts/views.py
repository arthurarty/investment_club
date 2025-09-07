from django.shortcuts import render
from django.views import View


class LoginView(View):
    def get(self, request):
        context = {}
        return render(request, "accounts/index.html", context)
