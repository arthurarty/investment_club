from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from clubs.forms.club_membership_form import MemberLookupForm


class MemberLookUpView(LoginRequiredMixin, View):
    """
    View to look up and display member details.
    """

    def get(self, request):
        """
        Handle GET requests to display member details.
        """
        # Placeholder for actual member lookup logic
        context = {
            "look_up_form": MemberLookupForm(),
            "user": request.user,
        }
        return render(request, "clubs/member_lookup.html", context)
