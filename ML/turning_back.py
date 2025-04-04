# turning_back.py
from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime
import mysql.connector
import shutil
import os

# If running as client, use Paramiko + SCP for SSH connection
IS_CLIENT = False  # Change to True if running on the client

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = False
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Top_Corner.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"   # Host media folder
ACTION_NAME = "Turning Back"
TURNING_THRESHOLD = 10    # consecutive frames needed
# ========================

# ========================
# SSH CONFIG (Only if client)
# ========================
if IS_CLIENT:
    hostname = "172.16.30.203"  # Host system IP
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)

    scp = SCPClient(ssh.get_transport())

    # Remote DB from client
    db = mysql.connector.connect(
        host=hostname,
        port=3306,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
else:
    # Local DB connection on host
    db = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

cursor = db.cursor()

# ========================
# Load YOLOv8 pose model
# ========================
pose_model = YOLO(POSE_MODEL_PATH)

# ========================
# Video source
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)


def is_turning_back(keypoints):
    """
    Basic check for turning back using nose, eyes, ears, shoulders.
    """
    if keypoints is None or len(keypoints) < 7:
        return False

    nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder = keypoints[:7]

    if any(pt is None for pt in [nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder]):
        return False

    eye_dist = abs(left_eye[0] - right_eye[0])
    shoulder_dist = abs(left_shoulder[0] - right_shoulder[0])

    return eye_dist < 0.4 * shoulder_dist and left_ear[0] > left_eye[0] and right_ear[0] < right_eye[0]


malpractice = 0
video_control = 0

while cap.isOpened():
    turning_back_check = []
    turning_back = False

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # --------------------------
    # Overlays for date/time
    # --------------------------
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')  # 12-hour
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(frame, overlay_text, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255,255,255), 2, cv2.LINE_AA)

    lecture_hall_text = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_text, (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    pose_results = pose_model(frame)

    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []
        for kp in keypoints:
            if is_turning_back(kp):
                malpractice += 1
                turning_back = True
                cv2.putText(frame, ACTION_NAME + "!", (850, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                # Mark first 6 keypoints in red
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
            else:
                # Mark first 6 keypoints in green if not turning
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # Additional keypoints in green
            for x, y in kp[6:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            turning_back_check.append(turning_back)

    # Start or continue recording
    if malpractice >= 1:
        if video_control == 0:
            video_control = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output_turningback.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        out.write(frame)

    # If no one is turning back => maybe finalize
    if True not in turning_back_check:
        if malpractice >= TURNING_THRESHOLD:
            # Finalize
            if video_control == 1:
                out.release()

            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')

            # Lecture Hall ID
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"output_{timestamp}.mp4"

            # Copy local temp file to final name in host media dir
            local_temp = "output_turningback.mp4"
            dest_path = os.path.join(MEDIA_DIR, proof_filename)
            shutil.copy(local_temp, dest_path)

            # If running as client => scp to remote
            if IS_CLIENT:
                remote_dest = f"./Documents/Repos/DetectSus/application/application/media/{proof_filename}"
                scp.put(local_temp, remote_dest)

            # DB Insert
            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
            cursor.execute(sql, values)
            db.commit()

            malpractice = 0
            video_control = 0
        else:
            if video_control == 1:
                out.release()
                malpractice = 0
                video_control = 0

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if IS_CLIENT:
    scp.close()
    ssh.close()
cv2.destroyAllWindows()
