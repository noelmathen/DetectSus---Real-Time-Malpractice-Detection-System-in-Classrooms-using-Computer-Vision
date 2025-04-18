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
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_sms_notification
from .forms import EditProfileForm, TeacherProfileForm
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from .utils import ssh_run_script, local_run_script
import threading
import os
import subprocess
from .utils import RUNNING_SCRIPTS 
import time

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

        return redirect('login')  # Or any success page
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
def profile_view(request):
    """Render the user's profile page (the one you already have)."""
    return render(request, 'profile.html')  # Your existing page


@login_required
def edit_profile(request):
    """Allow user to edit basic info (User) + teacher-specific info (TeacherProfile)."""
    user = request.user
    # Attempt to fetch or create the TeacherProfile:
    teacher_profile, _ = TeacherProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = EditProfileForm(request.POST, instance=user)
        profile_form = TeacherProfileForm(request.POST, request.FILES, instance=teacher_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = EditProfileForm(instance=user)
        profile_form = TeacherProfileForm(instance=teacher_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'edit_profile.html', context)


@login_required
def change_password(request):
    """Allow user to change their password using Django's built-in PasswordChangeForm."""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Important! Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please fix the error below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'change_password.html', {'form': form})



@login_required
def malpractice_log(request):
    # Retrieve filter parameters from the GET request
    date_filter = request.GET.get('date', '').strip()
    time_filter = request.GET.get('time', '').strip()
    malpractice_filter = request.GET.get('malpractice_type', '').strip()
    building_filter = request.GET.get('building', '').strip()
    query = request.GET.get('q', '').strip()
    faculty_filter = request.GET.get('faculty', '').strip()
    assignment_filter = request.GET.get('assigned', '').strip()
    review_filter = request.GET.get('review', '').strip() or 'not_reviewed'


    # Base Queryset based on user role
    if request.user.is_superuser:
        logs = MalpraticeDetection.objects.all()
        # Apply review filter for admin
        if review_filter.lower() == 'reviewed':
            logs = logs.filter(verified=True)
        elif review_filter.lower() == 'not_reviewed':
            logs = logs.filter(verified=False)
    else:
        assigned_halls = LectureHall.objects.filter(assigned_teacher=request.user)
        logs = MalpraticeDetection.objects.filter(
            lecture_hall__in=assigned_halls,
            verified=True,
            is_malpractice=True
        )

    # Apply Filtering
    if date_filter:
        logs = logs.filter(date=date_filter)
    if time_filter:
        if time_filter.upper() == "FN":
            logs = logs.filter(time__lt="12:00:00")
        elif time_filter.upper() == "AN":
            logs = logs.filter(time__gte="12:00:00")
    if malpractice_filter:
        logs = logs.filter(malpractice=malpractice_filter)
    if building_filter:
        logs = logs.filter(lecture_hall__building=building_filter)
    if query:
        logs = logs.filter(lecture_hall__hall_name__icontains=query)
    if faculty_filter:
        logs = logs.filter(lecture_hall__assigned_teacher__id=faculty_filter)
    if assignment_filter:
        if assignment_filter.lower() == "assigned":
            logs = logs.filter(lecture_hall__assigned_teacher__isnull=False)
        elif assignment_filter.lower() == "unassigned":
            logs = logs.filter(lecture_hall__assigned_teacher__isnull=True)

    # if review_filter:
    #     if review_filter.lower() == 'reviewed':
    #         logs = logs.filter(verified=True)
    #     elif review_filter.lower() == 'not_reviewed':
    #         logs = logs.filter(verified=False)

    logs = logs.order_by('-date', '-time')

    # Update session record count to trigger alert if new logs appear
    record_count = logs.count()
    alert = False
    if "record_count" in request.session:
        if request.session["record_count"] < record_count:
            alert = True
            request.session["record_count"] = record_count
    else:
        request.session["record_count"] = record_count

    context = {
        'result': logs,
        'alert': alert,
        'is_admin': request.user.is_superuser,
        'date_filter': date_filter,
        'time_filter': time_filter,
        'malpractice_filter': malpractice_filter,
        'building_filter': building_filter,
        'query': query,
        'faculty_filter': faculty_filter,
        'assignment_filter': assignment_filter,
        'review_filter': review_filter,  # Pass review filter to template
        'faculty_list': User.objects.filter(teacherprofile__isnull=False, is_superuser=False),
        'buildings': LectureHall.objects.values_list('building', flat=True).distinct(),
    }

    return render(request, 'malpractice_log.html', context)



@csrf_exempt
@login_required
@user_passes_test(is_admin)
def review_malpractice(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        data = json.loads(request.body)
        proof_filename = data.get('proof')
        decision = data.get('decision')

        if not proof_filename or decision not in ['yes', 'no']:
            return JsonResponse({'success': False, 'error': 'Invalid data received'})

        # Find the malpractice log
        try:
            log = MalpraticeDetection.objects.get(proof=proof_filename)
        except MalpraticeDetection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Malpractice log not found'})

        # Update the log
        log.verified = True
        log.is_malpractice = (decision == 'yes')
        log.save()

        # If approved as malpractice, notify the assigned teacher
        if log.is_malpractice and log.lecture_hall and log.lecture_hall.assigned_teacher:
            teacher_user = log.lecture_hall.assigned_teacher

            try:
                teacher_profile = teacher_user.teacherprofile
            except TeacherProfile.DoesNotExist:
                print(f"[WARN] No profile found for user: {teacher_user.username}")
                teacher_profile = None

            # Send Email Notification
            subject = 'Malpractice Alert: New Case Reviewed'
            message_body = (
                f"Dear {teacher_user.get_full_name() or teacher_user.username},\n\n"
                f"A malpractice has been detected in your classroom and has been approved by the examination cell.\n\n"
                f"Details:\n"
                f"- 📅 Date: {log.date}\n"
                f"- ⏰ Time: {log.time}\n"
                f"- 🎯 Type: {log.malpractice}\n"
                f"- 🏫 Lecture Hall: {log.lecture_hall.building} - {log.lecture_hall.hall_name}\n\n"
                f"You can view the recorded video proof from your DetectSus portal.\n\n"
                f"Best regards,\nDetectSus Team"
            )

            try:
                send_mail(subject, message_body, settings.EMAIL_HOST_USER, [teacher_user.email], fail_silently=False)
            except Exception as e:
                print(f"\n[ERROR] Email sending failed: {e}\n")

            # Send SMS Notification if phone is available
            if teacher_profile and teacher_profile.phone:
                sms_message_body = (
                    f'''
                    \nDear {teacher_user.get_full_name() or teacher_user.username},\n\n'''
                    f"🔔 Malpractice Alert\n"
                    f"{log.date} | {log.time}\n"
                    f"{log.malpractice} detected in {log.lecture_hall.building}-{log.lecture_hall.hall_name}.\n"
                    f"\nCheck DetectSus for video proof."
                )

                try:
                    send_sms_notification(f"+91{teacher_profile.phone.strip()}", sms_message_body)
                except Exception as e:
                    print(f"\n[ERROR] SMS sending failed: {e}\n")

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON format'})

    except Exception as e:
        print(f"[EXCEPTION] Unexpected error in review_malpractice: {e}")
        return JsonResponse({'success': False, 'error': 'Internal server error'})



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

    # Use the reverse relation "lecturehall" (LectureHall.assigned_teacher) 
    teachers = User.objects.filter(is_superuser=False).select_related('lecturehall')
    buildings = LectureHall.objects.values_list('building', flat=True).distinct()

    if assigned_filter == 'assigned':
        teachers = teachers.filter(lecturehall__isnull=False)
    elif assigned_filter == 'unassigned':
        teachers = teachers.filter(lecturehall__isnull=True)

    if building_filter:
        teachers = teachers.filter(lecturehall__building=building_filter)

    context = {
        'teachers': teachers,
        'buildings': buildings,
        'assigned_filter': assigned_filter,
        'building_filter': building_filter,
    }
    return render(request, 'view_teachers.html', context)




@login_required
@user_passes_test(is_admin)
def run_cameras_page(request):
    return render(request, 'run_cameras.html')



@login_required
@user_passes_test(lambda u: u.is_superuser) 
def trigger_camera_scripts(request):
    if request.method == 'POST':
        # List of configurations for each angle
        client_configs = [
            {
                "name": "Top Corner - Host(Allen 2)",
                "script_path": "C:\\Users\\noelm\\Documents\\PROJECTS\\DetectSus\\ML\\front.py",
                "mode": "local"
            },
            # {
            #     "name": "Top Corner Angle - Remote Client(Allen)",
            #     "ip": "192.168.154.9",
            #     "username": "allen",
            #     "password": "5213",
            #     "script_path": "D:\\application\\ML\\top_corner.py",
            #     "mode": "remote",
            #     "use_venv": False  # disable venv activation for this host
            # },
            # {
            #     "name": "Front Angle - Remote Client(Shruti)",
            #     "ip": "192.168.39.145",
            #     "username": "SHRUTI S",
            #     "password": "1234shibu",
            #     "script_path": "C:\\Users\\SHRUTI S\\Documents\\Repos\\DetectSus\\application\\application\\ML\\front.py",
            #     "mode": "remote",
            #     "use_venv": False 
            # },
            # {
            #     "name": "Front Angle - Remote Client(Noel)",
            #     "ip": "192.168.1.8",
            #     "username": "noelmathen",
            #     "password": "134652",
            #     "mode": "remote",
            #     "script_path": "C:\\Users\\noelmathen\\Documents\\PROJECTS\\DetectSus\\ML\\front.py",
            #     "use_venv": True
            # }
        ]

        # Function to run a given configuration
        def run_on_client(config):
            if config.get("mode") == "remote":
                use_venv = config.get("use_venv", True)
                venv_path = config.get("venv_path", None)
                success, output = ssh_run_script(
                    config["ip"],
                    config["username"],
                    config["password"],
                    config["script_path"],
                    use_venv,
                    venv_path
                )
                print(f"[{config['name']}]: {output if success else 'Error: ' + output}")
            elif config.get("mode") == "local":
                success, output = local_run_script(config["script_path"])
                print(f"[{config['name']}]: {output if success else 'Error: ' + output}")

        # Launch each script in a separate thread
        for config in client_configs:
            threading.Thread(target=run_on_client, args=(config,)).start()

        return JsonResponse({'status': 'started'})
    


@login_required
@user_passes_test(lambda u: u.is_superuser)
def stop_camera_scripts(request):
    if request.method == 'POST':
        # Iterate over a copy of the keys so we can safely remove items
        for key in list(RUNNING_SCRIPTS.keys()):
            handle = RUNNING_SCRIPTS[key]
            if handle.get("mode") == "remote":
                try:
                    channel = handle.get("channel")
                    if channel:
                        # Send Ctrl+C to the remote process
                        channel.send("\x03")
                        # Wait a moment for the remote process to handle the interrupt
                        time.sleep(2)
                        channel.close()
                    ssh = handle.get("ssh")
                    if ssh:
                        ssh.close()
                    print(f"\n[{key}] Remote process terminated successfully.")
                except Exception as e:
                    print(f"\n[{key}] Error terminating remote process: {e}")
            elif handle.get("mode") == "local":
                process = handle.get("process")
                if process:
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                        print(f"\n[{key}] Local process terminated successfully.")
                    except Exception as e:
                        print(f"\n[{key}] Error terminating local process: {e}")
            RUNNING_SCRIPTS.pop(key, None)
        return JsonResponse({"status": "stopped"})
    return JsonResponse({"error": "Invalid request method"}, status=400)




