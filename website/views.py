from datetime import date

from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

ROBOTS_TXT = """\
User-agent: Googlebot
Allow: /$
Disallow: /

User-agent: *
Disallow: /
"""


class LandingView(TemplateView):
    """
    Public landing page for the website.
    """

    template_name = "website/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_year"] = date.today().year
        return context


@require_GET
def robots_txt(request):
    """
    Allow only Google's crawler, and only on the landing page; block all
    other bots and all other pages.
    """
    return HttpResponse(ROBOTS_TXT, content_type="text/plain")
