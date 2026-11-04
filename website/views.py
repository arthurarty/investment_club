from datetime import date

from django.views.generic import TemplateView


class LandingView(TemplateView):
    """
    Public landing page for the website.
    """

    template_name = "website/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_year"] = date.today().year
        return context
