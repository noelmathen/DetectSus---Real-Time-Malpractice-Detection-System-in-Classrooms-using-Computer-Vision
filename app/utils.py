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


def ssh_run_script(ip, username, password, script_path, use_venv=True, venv_path=None):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        # Get the directory and filename of the script
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)
        
        # Determine activation command if a virtual environment is to be used
        if use_venv:
            # If no venv_path is provided, use the default location for this user
            if not venv_path:
                venv_path = f'C:/Users/{username}/Documents/PROJECTS/DetectSus/susenv/Scripts/activate.bat'
            activation_cmd = f'call "{venv_path}" && '
        else:
            activation_cmd = ""
        
        # Build the command using proper quoting; using cmd /c so the shell exits after execution
        command = f'cmd /c "cd /d \"{script_dir}\" && {activation_cmd}python \"{script_name}\""'
        
        stdin, stdout, stderr = ssh.exec_command(command)

        # Stream output (real-time)
        for line in iter(stdout.readline, ""):
            print(f"[{username}] {line.strip()}")
        
        # Read all outputs
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        if err:
            return False, err
        return True, out
    except Exception as e:
        return False, str(e)



# Helper function to run a script locally (host machine)
def local_run_script(script_path):
    try:
        # Get the directory and file name from the script_path
        script_dir = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)

        #Use this if there is virtual environemnet in host laptop also
        # activate = r'C:\Users\SHRUTI S\Documents\Repos\DetectSus\application\venv\Scripts\activate.bat'

        # # Build the command with proper quoting to handle spaces in the paths.
        # command = 'cmd /c "cd /d \"{}\" && call \"{}\" && python \"{}\""'.format(
        #     script_dir, activate, script_name
        # )


        # Build the command without virtual environment activation.
        # Using proper quoting to handle spaces in the paths.
        command = 'cmd /c "cd /d \"{}\" && python \"{}\""'.format(
            script_dir, script_name
        )

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )

        # Optionally, stream the output line-by-line
        for line in process.stdout:
            print(f"[Local - Host] {line.strip()}")

        out, err = process.communicate()
        if process.returncode != 0:
            return False, err
        return True, out
    except Exception as e:
        return False, str(e)