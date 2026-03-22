from clubs.models import (
    Club,
)


def is_club_admin_or_creator(request, club: Club) -> bool:
    """
    Check if the user can manage club financials (create financial years, dues, etc).
    User must be a member and either the club creator or an admin.
    Returns bool.
    """
    is_creator = club.created_by_id == request.user.id
    club_member = club.members.filter(user=request.user).first()
    if not club_member:
        return False
    can_create = is_creator or club_member.is_admin
    if not can_create:
        return False
    return True
