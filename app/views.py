# views.py
from django.shortcuts import render
from django.shortcuts import redirect
from .models import *
from threading import Event
from django.http import JsonResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import TeacherProfile
import json
from django.db.models import Q



# Global stop event
stop_event = Event()

def is_admin(user):
    return user.is_superuser


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

        # return redirect('login')  # Or any success page
    return render(request, 'teacher_register.html')



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

def login(request):
    return render(request,'login.html')



@login_required
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
        try:
            teacher_profile = request.user.teacherprofile
        except TeacherProfile.DoesNotExist:
            logs = MalpraticeDetection.objects.none()
        else:
            # Get the actual LectureHall objects (or their IDs)
            assigned_halls = LectureHall.objects.filter(assigned_teacher=request.user)
            logs = MalpraticeDetection.objects.filter(
                lecture_hall__in=assigned_halls,
                verified=True,
                is_malpractice=True
            ).order_by('-date', '-time')

    record_count = logs.count()
    alert = False
    if "record_count" in request.session:
        if request.session["record_count"] < record_count:
            alert = True
            request.session["record_count"] = record_count
    else:
        request.session["record_count"] = record_count

    return render(request, 'malpractice_log.html', {
        'result': logs,
        'alert': alert,
        'is_admin': request.user.is_superuser
    })




@csrf_exempt
@login_required
@user_passes_test(is_admin)
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



@login_required
@user_passes_test(is_admin)
def manage_lecture_halls(request):
    teachers = User.objects.filter(is_superuser=False)
    error_message = None
    query = request.GET.get('q', '')
    building_filter = request.GET.get('building', '')
    assignment_filter = request.GET.get('assigned', '')

    buildings = LectureHall.objects.values_list('building', flat=True).distinct()
    lecture_halls = LectureHall.objects.all()

    if query:
        lecture_halls = lecture_halls.filter(hall_name__icontains=query)
    if building_filter:
        lecture_halls = lecture_halls.filter(building=building_filter)
    if assignment_filter == "assigned":
        lecture_halls = lecture_halls.exclude(assigned_teacher=None)
    elif assignment_filter == "unassigned":
        lecture_halls = lecture_halls.filter(assigned_teacher=None)

    if request.method == 'POST':
        if 'add_hall' in request.POST:
            hall_name = request.POST.get('hall_name')
            building = request.POST.get('building')
            if hall_name and building:
                if LectureHall.objects.filter(hall_name=hall_name, building=building).exists():
                    error_message = f"Lecture Hall '{hall_name}' already exists in '{building}'."
                else:
                    LectureHall.objects.create(hall_name=hall_name, building=building)
                    return redirect('manage_lecture_halls')

        elif 'map_teacher' in request.POST:
            teacher_id = request.POST.get('teacher_id')
            hall_id = request.POST.get('hall_id')
            try:
                hall = LectureHall.objects.get(id=hall_id)
                teacher = User.objects.get(id=teacher_id)
                LectureHall.objects.filter(assigned_teacher=teacher).update(assigned_teacher=None)
                hall.assigned_teacher = teacher
                hall.save()
                return redirect('manage_lecture_halls')
            except:
                pass

    return render(request, 'manage_lecture_halls.html', {
        'lecture_halls': lecture_halls,
        'teachers': teachers,
        'buildings': buildings,
        'error_message': error_message,
        'query': query,
        'building_filter': building_filter,
        'assignment_filter': assignment_filter
    })



@login_required
@user_passes_test(is_admin)
def view_teachers(request):
    assigned_filter = request.GET.get('assigned', '')
    building_filter = request.GET.get('building', '')

    teachers = User.objects.filter(is_superuser=False).select_related('teacherprofile')
    buildings = LectureHall.objects.values_list('building', flat=True).distinct()

    if assigned_filter == 'assigned':
        teachers = teachers.filter(teacherprofile__lecture_hall__isnull=False)
    elif assigned_filter == 'unassigned':
        teachers = teachers.filter(teacherprofile__lecture_hall__isnull=True)

    if building_filter:
        teachers = teachers.filter(teacherprofile__lecture_hall__building=building_filter)

    context = {
        'teachers': teachers,
        'buildings': buildings,
        'assigned_filter': assigned_filter,
        'building_filter': building_filter,
    }
    return render(request, 'view_teachers.html', context)

