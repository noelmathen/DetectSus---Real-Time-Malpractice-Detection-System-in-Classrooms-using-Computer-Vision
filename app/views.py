# views.py
from django.shortcuts import render
from django.shortcuts import redirect
from .models import *
from threading import Event
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import TeacherProfile
import json

# Global stop event
stop_event = Event()


def home(request):
    return render(request,'index.html')


def index(request):
    return render(request,'index.html')


def teacher_register(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        profile_picture = request.FILES['profile_picture']

        # Create User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Save profile
        profile = TeacherProfile(user=user, phone=phone, profile_picture=profile_picture)
        profile.save()

        return redirect('login')  # Or any success page
    return render(request, 'teacher_register.html')



def login(request):
    return render(request,'login.html')


def addlogin(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            return redirect('index')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})



def logout(request):
    auth_logout(request)
    return redirect('index')

@login_required
def profile(request):
    return render(request, 'profile.html')  # assuming your template is in templates/profile.html


@login_required
def malpractice_log(request):
    if request.user.is_superuser:
        logs = MalpraticeDetection.objects.all().order_by('-date', '-time')
    else:
        logs = MalpraticeDetection.objects.filter(verified=True, is_malpractice=True).order_by('-date', '-time')  # Only show approved logs

    record_count = MalpraticeDetection.objects.count()
    alert = False

    if "record_count" in request.session:
        if request.session["record_count"] < record_count:
            alert = True
            request.session["record_count"] = record_count
    else:
        request.session["record_count"] = record_count

    context = {
        "result": logs,
        "alert": alert,
        "is_admin": request.user.is_superuser
    }
    return render(request, "malpractice_log.html", context)



@csrf_exempt
@login_required
def review_malpractice(request):
    if request.method == 'POST' and request.user.is_superuser:
        data = json.loads(request.body)
        proof_filename = data.get('proof')
        decision = data.get('decision')

        try:
            log = MalpraticeDetection.objects.get(proof=proof_filename)
            log.verified = True
            log.is_malpractice = True if decision == 'yes' else False
            log.save()
            return JsonResponse({'success': True})
        except MalpraticeDetection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Log not found'})
    return JsonResponse({'success': False, 'error': 'Unauthorized or bad request'})


def upload(request):
    return render(request,'result.html')



