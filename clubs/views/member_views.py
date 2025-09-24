from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from accounts.models import CustomUser as User
from clubs.forms.club_membership_form import MemberLookupForm
from clubs.models import Club, ClubMember


class MemberLookUpView(LoginRequiredMixin, View):
    """
    View to look up and display member details.
    """

    def post(self, request, club_id: int):
        """
        Handle POST requests to look up a member by email.
        """
        club = Club.objects.get(id=club_id)
        if not club:
            # Todo: Add message to inform user that the club does not exist.
            return redirect("clubs:index")
        if not ClubMember.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        form = MemberLookupForm(request.POST)
        if not form.is_valid():
            context = {
                "look_up_form": form,
            }
            return render(request, "clubs/member_lookup.html", context)
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
            context = {
                "look_up_form": form,
                "member": user,
                "email": email,
                "club": club,
            }
            return render(request, "clubs/member_lookup.html", context)
        except User.DoesNotExist:
            form.add_error("email", "No user found with this email address.")
        context = {
            "look_up_form": form,
            "email": email,
        }
        return render(request, "clubs/member_lookup.html", context)


class ClubMemberView(LoginRequiredMixin, View):
    """
    View to add a member to a club.
    """

    def get(self, request, club_id: int):
        """
        Handle get requests to add a member to a club.
        """
        club = Club.objects.get(id=club_id)
        if not club:
            return redirect("clubs:index")
        if not ClubMember.objects.filter(
            club=club, user=request.user, is_admin=True
        ).exists():
            # Todo: Add message to inform user that they do not have permission to view this page.
            return redirect("clubs:detail", club_id=club.id)
        form = MemberLookupForm(request.GET)
        if not form.is_valid():
            return redirect("clubs:detail", club_id=club.id)
        user = User.objects.filter(email=form.cleaned_data["email"]).first()
        if not user:
            return redirect("clubs:detail", club_id=club.id)
        ClubMember.objects.get_or_create(club=club, user=user, is_admin=False)
        return redirect("clubs:detail", club_id=club.id)
