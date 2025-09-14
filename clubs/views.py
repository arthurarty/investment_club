from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View


class ClubsView(LoginRequiredMixin, View):
    """
    View to display a list of investment clubs.
    """

    def get(self, request):
        """
        Handle GET requests to display the list of clubs.
        """
        # Logic to retrieve and display clubs would go here
        context = {}
        return render(request, "clubs/index.html", context)
