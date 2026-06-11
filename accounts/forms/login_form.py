from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV3


class LoginForm(forms.Form):
    """
    Form for user login.
    """

    email = forms.EmailField(label="Email", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
    captcha = ReCaptchaField(widget=ReCaptchaV3)
