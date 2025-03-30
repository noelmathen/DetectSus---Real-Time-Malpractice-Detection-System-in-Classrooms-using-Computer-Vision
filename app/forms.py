# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import TeacherProfile

class EditProfileForm(forms.ModelForm):
    """Updates basic User info like first_name, last_name, email."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class TeacherProfileForm(forms.ModelForm):
    """For updating teacher-specific fields, e.g. phone, profile_picture."""
    class Meta:
        model = TeacherProfile
        fields = ['phone', 'profile_picture']
