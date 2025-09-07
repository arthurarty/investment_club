from django import forms


class LoginForm(forms.Form):
    """
    Form for user login.
    """

    email = forms.EmailField(label="Email", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)
