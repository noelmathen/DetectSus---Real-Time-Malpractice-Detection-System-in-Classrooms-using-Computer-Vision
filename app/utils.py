# utils.py
from django.conf import settings
from twilio.rest import Client
import paramiko


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


def ssh_run_script(ip, username, password, script_path):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        stdin, stdout, stderr = ssh.exec_command(f"python3 {script_path}")
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()

        if err:
            return False, err
        return True, out
    except Exception as e:
        return False, str(e)

