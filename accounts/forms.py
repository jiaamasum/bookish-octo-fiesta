from django import forms
from django.contrib.auth.forms import PasswordResetForm


class EmailExistsPasswordResetForm(PasswordResetForm):
    """
    Override default reset form to surface an error when the email
    is not associated with any user, instead of silently succeeding.
    """

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not list(self.get_users(email)):
            raise forms.ValidationError("No account found with that email.")
        return email
