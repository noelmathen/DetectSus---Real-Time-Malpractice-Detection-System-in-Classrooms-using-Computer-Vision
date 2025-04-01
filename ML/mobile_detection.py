#mobile_detection.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = False  # Change to True if running as client

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = True
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Phone_2.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Model for mobile detection
MOBILE_MODEL_PATH = "yolo11m.pt"
MEDIA_DIR = "../media/"
ACTION_NAME = "Mobile Phone Detected"

# Minimum consecutive frames with a phone to confirm event
MOBILE_THRESHOLD = 3
# ========================

# ========================
# SSH CONFIG (Only if client)
# ========================
if IS_CLIENT:
    hostname = "192.168.147.145"
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)

    scp = SCPClient(ssh.get_transport())

    # Remote DB
    db = mysql.connector.connect(
        host=hostname,
        port=3306,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
else:
    # Local DB
    db = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

cursor = db.cursor()

# ========================
# MODEL LOADING
# ========================
model = YOLO(MOBILE_MODEL_PATH)

# ========================
# VIDEO SOURCE
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# VARIABLES
# ========================
phone_in_progress = False  # Are we currently in a phone detection event?
phone_frames = 0           # Count how many consecutive frames had a phone
video_control = False      # Are we currently recording?
out = None

# ========================
# MAIN LOOP
# ========================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # 1) Overly day/date/time in top-left
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')  # 12-hour format with leading zeros
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()  # 'am' or 'pm'
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(frame, overlay_text, (50, 100),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    lecture_hall_name = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_name, (50, FRAME_HEIGHT - 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # 2) Model inference
    results = model(frame)
    mobile_detected = False

    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                # If class ID 67 => phone in COCO; adjust if needed
                if int(box.cls) == 67:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mobile_detected = True
                    # Draw bounding box + label
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                    cv2.putText(frame, "Mobile", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    # 3) If phone is detected this frame
    if mobile_detected:
        # If we weren't previously detecting a phone event => start
        if not phone_in_progress:
            phone_in_progress = True
            phone_frames = 1
            # Start recording if not already
            if not video_control:
                video_control = True
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter("output.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        else:
            # Already in progress, so just increment frame count
            phone_frames += 1

        cv2.putText(frame, ACTION_NAME + "!", (850, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Write to video if recording
        if video_control and out is not None:
            out.write(frame)

    else:
        # No phone in this frame
        # If we had an ongoing detection event, finalize it
        if phone_in_progress:
            phone_in_progress = False
            # phone_frames has total consecutive phone frames
            if phone_frames >= MOBILE_THRESHOLD:
                # finalize and insert into DB
                if video_control and out is not None:
                    out.release()

                now_save = datetime.now()
                date_db = now_save.date().isoformat()
                time_db = now_save.time().strftime('%H:%M:%S')

                # Lecture hall ID
                cursor.execute(
                    "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                    (LECTURE_HALL_NAME, BUILDING)
                )
                hall_result = cursor.fetchone()
                hall_id = hall_result[0] if hall_result else None

                timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                proof_filename = f"output_{timestamp}.mp4"
                destination_path = os.path.join(MEDIA_DIR, proof_filename)
                shutil.copy("output.mp4", destination_path)

                if IS_CLIENT:
                    from_path = "output.mp4"  # local
                    to_path = destination_path
                    scp.put(from_path, to_path)

                sql = """
                    INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
                cursor.execute(sql, values)
                db.commit()
            else:
                # Not enough consecutive phone frames => discard video
                if video_control and out is not None:
                    out.release()
                if os.path.exists("output.mp4"):
                    os.remove("output.mp4")

            # Reset counters
            phone_frames = 0
            video_control = False
            out = None
        else:
            # We are not in a phone_in_progress event => do nothing
            pass

    # If we are in progress and actively recording, keep saving frames
    if phone_in_progress and video_control and out is not None:
        out.write(frame)

    cv2.imshow("Exam Monitoring - Mobile Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if video_control and out is not None:
    out.release()

if IS_CLIENT:
    scp.close()
    ssh.close()

cv2.destroyAllWindows()
