from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from clubs.forms.club_creation_form import ClubCreationForm
from clubs.models import Club


class ClubsView(LoginRequiredMixin, View):
    """
    View to display a list of investment clubs.
    """

    def get(self, request):
        """
        Handle GET requests to display the list of clubs.
        """
        current_user = request.user
        clubs = (
            Club.objects.filter(created_by=current_user)
            .order_by("created_at")
            .all()[:10]
        )
        context = {
            "clubs": clubs,
            "user": current_user,
            "create_club_form": ClubCreationForm(),
        }
        return render(request, "clubs/index.html", context)
