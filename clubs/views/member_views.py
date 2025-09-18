from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from clubs.forms.club_membership_form import MemberLookupForm


class MemberLookUpView(LoginRequiredMixin, View):
    """
    View to look up and display member details.
    """

    def post(self, request):
        """
        Handle POST requests to look up a member by email.
        """
        form = MemberLookupForm(request.POST)
        if not form.is_valid():
            context = {
                "look_up_form": form,
                "user": request.user,
            }
            return render(request, "clubs/member_lookup.html", context)
        email = form.cleaned_data["email"]
        context = {
            "look_up_form": form,
            "user": request.user,
            "email": email,
        }
        return render(request, "clubs/member_lookup.html", context)
