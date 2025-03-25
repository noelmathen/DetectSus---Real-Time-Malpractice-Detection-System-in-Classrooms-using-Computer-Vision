# models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin

class MalpraticeDetection(models.Model):
    date = models.DateField(null=True)
    time = models.TimeField(null=True)
    malpractice = models.CharField(max_length=150)
    proof = models.CharField(max_length=150)
    is_malpractice = models.BooleanField(null=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.malpractice} - {self.date} {self.time}"


class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to='profile_pics/')
    
    def __str__(self):
        return self.user.username
    
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'profile_picture']
    search_fields = ['user__username', 'phone'] 