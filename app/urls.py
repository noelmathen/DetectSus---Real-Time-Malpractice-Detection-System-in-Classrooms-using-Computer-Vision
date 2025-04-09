# urls.py
from django.contrib import admin
from django.urls import path
from . import views
from django.conf.urls import url
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home',views.home),
    path('',views.index),
    path('index', views.index, name='index'),
    path('register/teacher/', views.teacher_register, name='teacher_register'),
    path('login/addlogin', views.addlogin, name='addlogin'),
    path('login/',views.login, name='login'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('logout/',views.logout, name='logout'),
    path('malpractice_log/',views.malpractice_log, name='malpractice_log'),
    path('review_malpractice/', views.review_malpractice, name='review_malpractice'),
    path('manage-lecture-halls/', views.manage_lecture_halls, name='manage_lecture_halls'),
    path('view_teachers/', views.view_teachers, name='view_teachers'),
    path('run_cameras/', views.run_cameras_page, name='run_cameras_page'),
    path('trigger_camera_scripts/', views.trigger_camera_scripts, name='trigger_camera_scripts'),
    path('stop_camera_scripts/', views.stop_camera_scripts, name='stop_camera_scripts'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)