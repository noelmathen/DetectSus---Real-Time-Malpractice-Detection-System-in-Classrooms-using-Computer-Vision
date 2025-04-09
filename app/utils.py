# utils.py
from django.conf import settings
from twilio.rest import Client
import paramiko
import os
import subprocess

def send_sms_notification(to_phone, message_body):
    """
    Sends an SMS to the specified phone number using Twilio.
    :param to_phone: str -> phone number in E.164 format, e.g. +919876543210
    :param message_body: str -> The text message
    """
    # print(to_phone)
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    from_phone = settings.TWILIO_PHONE_NUMBER

    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message_body,
        from_=from_phone,
        to=to_phone
    )



RUNNING_SCRIPTS = {}

def ssh_run_script(ip, username, password, script_path, use_venv=True, venv_path=None):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        # Get the directory and file name of the script
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        
        # Determine activation command if a virtual environment is to be used
        if use_venv:
            if not venv_path:
                venv_path = f'C:/Users/{username}/Documents/PROJECTS/DetectSus/susenv/Scripts/activate.bat'
            activation_cmd = f'call "{venv_path}" && '
        else:
            activation_cmd = ""
        
        # Build the command using proper quoting; use cmd /c so the shell exits after execution
        command = f'cmd /c "cd /d \"{script_dir}\" && {activation_cmd}python \"{script_name}\""'
        
        # Open a session with a pseudo-terminal; this allows us to send Ctrl+C later.
        channel = ssh.get_transport().open_session()
        channel.get_pty()
        channel.exec_command(command)
        
        # Optionally, you can start a thread to read output asynchronously.
        # For now, we just store the SSH client and channel in our global dictionary.
        key = f"{username}_{script_name}"
        RUNNING_SCRIPTS[key] = {
            "mode": "remote",
            "ssh": ssh,
            "channel": channel
        }
        print(f"\n[{username}] Remote script {script_name} started.")
        return True, "Remote script started successfully."
    except Exception as e:
        return False, str(e)


def local_run_script(script_path):
    try:
        # Get the directory and file name from the script_path
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)

        # Build the command without virtual environment activation.
        command = 'cmd /c "cd /d \"{}\" && python \"{}\""'.format(
            script_dir, script_name
        )

        # Start the process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )

        key = f"local_{script_name}"
        RUNNING_SCRIPTS[key] = {
            "mode": "local",
            "process": process
        }
        print(f"[Local] Script {script_name} started.")
        return True, "Local script started successfully."
    except Exception as e:
        return False, str(e)  


