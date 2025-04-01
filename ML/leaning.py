# leaning.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = False  # Change to False if running on host

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = False
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Front.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

# Database Credentials
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"
ACTION_NAME = "Leaning"
# Leaning threshold for saving to DB
LEARNING_THRESHOLD = 3
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

    # Connect to remote DB from client
    db = mysql.connector.connect(
        host=hostname,
        port=3306,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
else:
    # Local DB connection if host
    db = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

cursor = db.cursor()

# Load YOLOv8 pose model
pose_model = YOLO(POSE_MODEL_PATH)

# Capture source
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

def is_leaning(keypoints):
    """
    Improved leaning detection:
    - Ensures shoulders are not aligned vertically (to avoid small head tilts)
    - Checks if head is clearly shifted left or right beyond a realistic threshold
    - Ignores tiny deviations (e.g., slight head turns)
    """
    if keypoints is None or len(keypoints) < 7:
        return False

    nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder = keypoints[:7]

    if any(pt is None for pt in [nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder]):
        return False

    eye_dist = abs(left_eye[0] - right_eye[0])
    shoulder_dist = abs(left_shoulder[0] - right_shoulder[0])
    shoulder_height_diff = abs(left_shoulder[1] - right_shoulder[1])
    head_center_x = (left_eye[0] + right_eye[0]) / 2
    shoulder_center_x = (left_shoulder[0] + right_shoulder[0]) / 2

    # Reject small tilts and head turns
    if eye_dist > 0.35 * shoulder_dist:
        return False

    # Ensure shoulders are not vertically misaligned (improper posture)
    if shoulder_height_diff > 40:  # pixels
        return False

    # Check if head center shifted significantly from shoulder center
    if abs(head_center_x - shoulder_center_x) > 60:
        return True

    return False



malpractice = 0
video_control = 0

while cap.isOpened():
    lean_check = []
    leaning_detected = False
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # YOLO Pose Estimation
    pose_results = pose_model(frame)

    # -----------------------
    # Construct day/date/time overlay
    # -----------------------
    now = datetime.now()
    day_str = now.strftime('%a')        # e.g. Wed
    date_str = now.strftime('%d-%m-%Y') # dd-mm-yyyy
    hour_12 = now.strftime('%I')  # 12-hour format with leading zeros
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()  # 'am' or 'pm'
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(
        frame, overlay_text, (50, 100),
        cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA
    )
    lecture_hall_name = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_name, (50, FRAME_HEIGHT - 50),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Process each person’s pose
    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []
        for kp in keypoints:
            if is_leaning(kp):
                malpractice += 1
                cv2.putText(frame, ACTION_NAME + "!", (850, 100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                # Mark keypoints in red
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
                leaning_detected = True

            # If not leaning, mark keypoints in green
            if not leaning_detected:
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # Also mark additional keypoints (if any after index 6) in green
            for x, y in kp[6:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            lean_check.append(leaning_detected)

    # Start video recording if we detect at least 1 leaning
    if malpractice >= 1:
        if video_control == 0:
            video_control = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output_leaning.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        out.write(frame)

    # If no leaning in this frame => check if we should finalize
    if True not in lean_check:
        if malpractice >= LEARNING_THRESHOLD:
            now_save = datetime.now()
            date_db = now_save.date().isoformat()          # e.g. 2025-03-24
            time_db = now_save.time().strftime('%H:%M:%S') # e.g. 14:53:12

            # Get lecture hall ID
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"output_{timestamp}.mp4"
            destination_path = os.path.join(MEDIA_DIR, proof_filename)
            if video_control == 1:
                out.release()

            shutil.copy("output_leaning.mp4", destination_path)

            # If client, also scp to remote
            if IS_CLIENT:
                scp.put("output_leaning.mp4", destination_path)

            # Insert detection event in DB
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
