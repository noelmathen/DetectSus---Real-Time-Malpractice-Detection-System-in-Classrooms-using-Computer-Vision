# hand_raise.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = False  # Change to True if running on client
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
MEDIA_DIR = "../media/"  # Where final proof file is stored on host
ACTION_NAME = "Hand Raised"
HAND_RAISE_THRESHOLD = 5
# ========================

# ========================
# SSH CONFIG (If client)
# ========================
if IS_CLIENT:
    hostname = "172.16.30.203"
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)
    scp = SCPClient(ssh.get_transport())

    # Connect to remote DB
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
# Load YOLOv8 pose model
# ========================
pose_model = YOLO(POSE_MODEL_PATH)

# ========================
# Video Source
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

def is_hand_raised(keypoints):
    """
    Detect if a student is raising their hand based on keypoint positions.
    """
    if keypoints is None or len(keypoints) < 11:
        return False

    # Shoulders, Elbows, Wrists => indices 5:11
    l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist = keypoints[5:11]
    if any(pt is None for pt in [l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist]):
        return False

    # Shoulder height threshold
    threshold = min(l_shoulder[1], r_shoulder[1]) + 30

    # If either wrist is above shoulder threshold
    if l_wrist[1] < threshold or r_wrist[1] < threshold:
        return True
    return False

malpractice = 0
video_control = False

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # Overlay day/time
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(frame, overlay_text, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    lecture_hall_name = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_name, (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # YOLO pose inference
    pose_results = pose_model(frame)

    hand_raised_check = []
    hand_raised = False

    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints else []
        for kp in keypoints:
            if is_hand_raised(kp):
                # If hand is raised
                malpractice += 1
                hand_raised = True
                cv2.putText(frame, ACTION_NAME + "!", (850, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                # Mark relevant keypoints in red
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
            else:
                # Mark those same keypoints in green if not raised
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # The rest of the keypoints in green
            for x, y in kp[:6]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            for x, y in kp[11:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            hand_raised_check.append(hand_raised)

    # Start video if we see at least 1 hand raised
    if malpractice >= 1 and not video_control:
        video_control = True
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter("output_handraise.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))

    # If we are recording, write frames
    if video_control:
        out.write(frame)

    # If no one is raising their hand => maybe finalize
    if True not in hand_raised_check:
        if malpractice >= HAND_RAISE_THRESHOLD:
            # finalize => rename + DB insert
            if video_control:
                out.release()

            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')
            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"output_{timestamp}.mp4"

            # Copy local file to media
            local_temp = "output_handraise.mp4"
            destination_path = os.path.join(MEDIA_DIR, proof_filename)
            shutil.copy(local_temp, destination_path)

            # If client => scp
            if IS_CLIENT:
                remote_path = f"./Documents/Repos/DetectSus/application/application/media/{proof_filename}"
                scp.put(local_temp, remote_path)

            # Insert into DB
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
            cursor.execute(sql, values)
            db.commit()

            malpractice = 0
            video_control = False
        else:
            # Not enough frames => discard
            if video_control:
                out.release()
                if os.path.exists("output_handraise.mp4"):
                    os.remove("output_handraise.mp4")
            malpractice = 0
            video_control = False

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if video_control:
    out.release()

if IS_CLIENT:
    scp.close()
    ssh.close()

cv2.destroyAllWindows()
