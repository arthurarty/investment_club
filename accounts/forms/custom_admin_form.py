from django.contrib.admin.forms import AdminAuthenticationForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3


class CustomAdminLoginForm(AdminAuthenticationForm):
    """
    Add Google Recaptcha to admin login page.
    """

    captcha = ReCaptchaField(widget=ReCaptchaV3)

    def clean(self):
        # Custom validation logic
        return super().clean()
