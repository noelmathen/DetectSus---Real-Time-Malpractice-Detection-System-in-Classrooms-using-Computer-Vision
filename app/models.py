# models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin


# Lecture Hall Model
class LectureHall(models.Model):
    BUILDING_CHOICES = [
        ('MAIN', 'Main Building'),
        ('KE', 'KE Block'),
        ('PG', 'PG Block'),
        # Add more if needed
    ]
    building = models.CharField(max_length=50, choices=BUILDING_CHOICES)
    hall_name = models.CharField(max_length=50)  # e.g. "LH1", "LH2", etc.
    assigned_teacher = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.building} - {self.hall_name}"




#Malpractice Logs Model
class MalpraticeDetection(models.Model):
    date = models.DateField(null=True)
    time = models.TimeField(null=True)
    malpractice = models.CharField(max_length=150)
    proof = models.CharField(max_length=150)
    is_malpractice = models.BooleanField(null=True)
    verified = models.BooleanField(default=False)
    lecture_hall = models.ForeignKey(LectureHall, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"{self.malpractice} - {self.date} {self.time}"


# Teacher Profile Model
class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to='profile_pics/')
    lecture_hall = models.OneToOneField(LectureHall, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.user.username
    
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'profile_picture']
    search_fields = ['user__username', 'phone'] 

