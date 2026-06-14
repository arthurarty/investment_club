from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.views import View

from accounts.forms.login_form import LoginForm
from accounts.forms.user_creation_form import UserCreationForm
from accounts.models import CustomUser
from clubs.forms.club_membership_form import MemberLookupForm


class LoginView(View):
    """
    View to handle user login.
    """

    def get(self, request):
        """
        Render the login form."""
        context = {"form": LoginForm()}
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
        return redirect("clubs:index")


def logout_view(request: HttpRequest):
    """
    Logout a user.
    """
    logout(request)
    return redirect("accounts:index")


class UserCreationView(LoginRequiredMixin, View):
    """
    View to create a user
    """

    def get(self, request):
        """
        Render the creation form
        """
        return render(
            request, "accounts/user_creation.html", {"form": UserCreationForm()}
        )

    def post(self, request):
        """
        Validates the form and creates a user.
        Does not set a password.
        """
        user_creation_form = UserCreationForm(request.POST)
        if not user_creation_form.is_valid():
            return render(
                request,
                "accounts/user_creation.html",
                {"form": user_creation_form},
            )
        created_user = CustomUser.objects.create_user(**user_creation_form.cleaned_data)
        context = {
            "look_up_form": MemberLookupForm(),
            "email": created_user.email,
            "member": created_user,
        }
        return render(request, "clubs/member_lookup.html", context)
