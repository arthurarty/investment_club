from django.forms import ModelForm

from clubs.models import Club


class ClubCreationForm(ModelForm):
    """
    From to create a new investment club.
    """

    class Meta:
        model = Club
        fields = ["name", "description", "contact_email", "contact_phone", "status"]
