# top.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = True  # Set True on client, False on host

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = True
CAMERA_INDEX = 0
VIDEO_PATH = "test_videos/Phone_2.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

MOBILE_MODEL_PATH = "yolo11m.pt"
MEDIA_DIR = "../media/"
ACTION_NAME = "Mobile Phone Detected"
MOBILE_THRESHOLD = 3
# ========================

# ========================
# SSH CONFIG (Client Only)
# ========================
if IS_CLIENT:
    hostname = "172.16.30.203"
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)

    scp = SCPClient(ssh.get_transport())

    db = mysql.connector.connect(
        host=hostname,
        port=3306,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
else:
    db = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

cursor = db.cursor()

# ========================
# LOAD MODEL AND VIDEO
# ========================
model = YOLO(MOBILE_MODEL_PATH)
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

phone_in_progress = False
phone_frames = 0
video_control = False
out = None

# ========================
# MAIN LOOP
# ========================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # Overlay: Day, Date, Time
    now = datetime.now()
    overlay_text = f"{now.strftime('%a')} | {now.strftime('%d-%m-%Y')} | {now.strftime('%I:%M:%S %p').lower()}"
    cv2.putText(frame, overlay_text, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
    lecture_hall_name = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_name, (50, FRAME_HEIGHT - 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Run detection
    results = model(frame)
    mobile_detected = False

    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                if int(box.cls) == 67:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mobile_detected = True
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                    cv2.putText(frame, "Mobile", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    if mobile_detected:
        if not phone_in_progress:
            phone_in_progress = True
            phone_frames = 1
            if not video_control:
                video_control = True
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter("output_mobiledetection.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        else:
            phone_frames += 1

        cv2.putText(frame, ACTION_NAME + "!", (850, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        if video_control and out is not None:
            out.write(frame)

    else:
        if phone_in_progress:
            phone_in_progress = False
            if phone_frames >= MOBILE_THRESHOLD:
                if video_control and out is not None:
                    out.release()

                now_save = datetime.now()
                timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                proof_filename = f"output_{timestamp}.mp4"
                date_db = now_save.date().isoformat()
                time_db = now_save.time().strftime('%H:%M:%S')

                # Get hall_id
                cursor.execute(
                    "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                    (LECTURE_HALL_NAME, BUILDING)
                )
                hall_result = cursor.fetchone()
                hall_id = hall_result[0] if hall_result else None

                # Copy to local media folder
                local_media_path = os.path.join(MEDIA_DIR, proof_filename)
                shutil.copy("output_mobiledetection.mp4", local_media_path)

                # Upload to host if client
                if IS_CLIENT:
                    remote_media_path = f"./Documents/Repos/DetectSus/application/application/media/{proof_filename}"
                    scp.put("output_mobiledetection.mp4", remote_media_path)

                # Log to DB
                sql = """
                    INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
                cursor.execute(sql, values)
                db.commit()
            else:
                if video_control and out is not None:
                    out.release()
                if os.path.exists("output_mobiledetection.mp4"):
                    os.remove("output_mobiledetection.mp4")

            phone_frames = 0
            video_control = False
            out = None

    if phone_in_progress and video_control and out is not None:
        out.write(frame)

    cv2.imshow("Exam Monitoring - Mobile Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Cleanup
cap.release()
if video_control and out is not None:
    out.release()
if IS_CLIENT:
    scp.close()
    ssh.close()
cv2.destroyAllWindows()