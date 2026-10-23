from clubs.models import Club

CURRENT_CLUB_SESSION_KEY = "current_club_id"


def current_club(request):
    """
    Expose the selected club and the user's clubs to the dashboard sidebar's
    club switcher.

    The club comes from the `club_id` URL kwarg when present, otherwise from
    the session (set by `ClubDetailView`). The session is only read here.
    """
    user = getattr(request, "user", None)
    match = getattr(request, "resolver_match", None)
    if user is None or not user.is_authenticated or match is None:
        return {}

    club_id = match.kwargs.get("club_id") or request.session.get(
        CURRENT_CLUB_SESSION_KEY
    )
    if club_id is None:
        return {}

    user_clubs = Club.objects.filter(members__user=user).order_by("name")
    sidebar_current_club = user_clubs.filter(id=club_id).first()
    if sidebar_current_club is None:
        return {}
    financial_years = list(
        sidebar_current_club.financial_years.order_by("-start_date", "-id")[:10]
    )
    latest_financial_year = financial_years[0] if financial_years else None
    financial_year_id = match.kwargs.get("financial_year_id")
    sidebar_current_financial_year = next(
        (fy for fy in financial_years if fy.id == financial_year_id),
        latest_financial_year,
    )
    return {
        "sidebar_current_club": sidebar_current_club,
        "sidebar_current_club_member_count": sidebar_current_club.members.count(),
        "sidebar_clubs": user_clubs[:10],
        "sidebar_financial_years": financial_years,
        "sidebar_latest_financial_year": latest_financial_year,
        "sidebar_current_financial_year": sidebar_current_financial_year,
    }
