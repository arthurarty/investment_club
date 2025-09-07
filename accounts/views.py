from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.views import View

from accounts.login_form import LoginForm


class LoginView(View):
    """
    View to handle user login.
    """

    def get(self, request):
        """
        Render the login form."""
        context = {}
        return render(request, "accounts/index.html", context)

    def post(self, request):
        """
        Given a POST request with email and password, authenticate the user.
        """
        login_form = LoginForm(request.POST)
        if not login_form.is_valid():
            return render(request, "accounts/failed_login.html", {})
        email = login_form.cleaned_data["email"]
        password = login_form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)
        if user is None:
            return render(request, "accounts/failed_login.html", {})
        login(request, user)
        context = {"user": user}
        return render(request, "accounts/successful_login.html", context)
