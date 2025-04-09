# top_corner.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko and scp
IS_CLIENT = True  # Set True on client, False on host

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = False
CAMERA_INDEX = 1
# VIDEO_PATH = "test_videos/Top_Corner.mp4"  # used if USE_CAMERA is False
VIDEO_PATH = "test_videos/Phone_2.mp4"  # used if USE_CAMERA is False

LECTURE_HALL_NAME = "LH1"
BUILDING = "Main Building"

DB_USER = "root"
DB_PASSWORD = "Detectsus1234"
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# For turning (pose) detection
POSE_MODEL_PATH = "yolov8n-pose.pt"
TURNING_BACK_ACTION = "Turning Back"
TURNING_THRESHOLD = 10

# For mobile phone detection
MOBILE_MODEL_PATH = "yolo11n.pt"
ACTION_NAME = "Mobile Phone Detected"
MOBILE_THRESHOLD = 3

# Media directory for saving video proofs
MEDIA_DIR = "../media/"

# ========================
# UTILITY: Turning Detection Checker
# ========================
def is_turning_back(kp):
    """
    Basic check for turning back using keypoints: nose, eyes, ears, shoulders.
    Expects at least the first 7 keypoints.
    """
    if kp is None or len(kp) < 7:
        return False

    nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder = kp[:7]
    if any(pt is None for pt in [nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder]):
        return False

    eye_dist = abs(l_eye[0] - r_eye[0])
    shoulder_dist = abs(l_shoulder[0] - r_shoulder[0])
    return (eye_dist < 0.4 * shoulder_dist and
            l_ear[0] > l_eye[0] and
            r_ear[0] < r_eye[0])

# ========================
# DATABASE SETUP
# ========================
if IS_CLIENT:
    # Remote DB settings (if running as client)
    hostname = "192.168.1.3"
    username = "allen"
    password_ssh = "5321"

    # Setup SSH connection and SCP for file transfer
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
    # Local DB
    db = mysql.connector.connect(
        host="localhost",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

cursor = db.cursor()

# ========================
# LOAD MODELS
# ========================
# Pose model for turning back detection
pose_model = YOLO(POSE_MODEL_PATH)
# Mobile detection model
mobile_model = YOLO(MOBILE_MODEL_PATH)

# ========================
# VIDEO CAPTURE SETUP
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
if not cap.isOpened():
    print("\nCamera could not be opened!")
else:
    print("\nCamera stream started!")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# STATE VARIABLES
# ========================
# For turning back detection
turning_in_progress = False
turning_frames = 0
turning_video = None
turning_recording = False

# For mobile phone detection
mobile_in_progress = False
mobile_frames = 0
mobile_video = None
mobile_recording = False

# ========================
# MAIN LOOP
# ========================

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        # ------------------------
        # Overlay Date/Time & Lecture Hall Info
        # ------------------------
        now = datetime.now()
        overlay_text = f"{now.strftime('%a')} | {now.strftime('%d-%m-%Y')} | {now.strftime('%I:%M:%S %p').lower()}"
        cv2.putText(frame, overlay_text, (50, 100),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
        hall_text = f"{LECTURE_HALL_NAME} | {BUILDING}"
        cv2.putText(frame, hall_text, (50, FRAME_HEIGHT - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # ------------------------
        # Turning Back Detection with Pose Model
        # ------------------------
        pose_results = pose_model(frame)
        turning_this_frame = False
        for result in pose_results:
            keypoints_arr = result.keypoints.xy.cpu().numpy() if result.keypoints else []
            for kp in keypoints_arr:
                if is_turning_back(kp):
                    turning_this_frame = True
                    # Mark the first 6 keypoints in red for turning
                    for x, y in kp[:6]:
                        cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
                else:
                    # Mark the first 6 keypoints in green if not turning
                    for x, y in kp[:6]:
                        cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
                # Mark remaining keypoints in green
                for x, y in kp[6:]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

        # Update state for turning detection
        if turning_this_frame:
            if not turning_in_progress:
                turning_in_progress = True
                turning_frames = 1
                if not turning_recording:
                    turning_recording = True
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    turning_video = cv2.VideoWriter("output_turningback.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            else:
                turning_frames += 1
            cv2.putText(frame, TURNING_BACK_ACTION + "!", (850, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        else:
            if turning_in_progress:
                turning_in_progress = False
                if turning_frames >= TURNING_THRESHOLD:
                    if turning_recording and turning_video:
                        turning_video.release()
                    now_save = datetime.now()
                    timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                    proof_filename = f"output_turningback_{timestamp}.mp4"
                    date_db = now_save.date().isoformat()
                    time_db = now_save.time().strftime('%H:%M:%S')
                    cursor.execute(
                        "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                        (LECTURE_HALL_NAME, BUILDING)
                    )
                    hall_result = cursor.fetchone()
                    hall_id = hall_result[0] if hall_result else None
                    local_temp = "output_turningback.mp4"
                    dest_path = os.path.join(MEDIA_DIR, proof_filename)
                    shutil.copy(local_temp, dest_path)
                    if IS_CLIENT:
                        remote_dest = f"./DetectSus/media/{proof_filename}"
                        scp.put(local_temp, remote_dest)
                    sql = """
                        INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    values = (date_db, time_db, TURNING_BACK_ACTION, proof_filename, hall_id)
                    cursor.execute(sql, values)
                    db.commit()
                else:
                    if turning_recording and turning_video:
                        turning_video.release()
                    if os.path.exists("output_turningback.mp4"):
                        os.remove("output_turningback.mp4")
                turning_frames = 0
                turning_recording = False
                turning_video = None

        if turning_in_progress and turning_recording and turning_video:
            turning_video.write(frame)

        # ------------------------
        # Mobile Phone Detection with Mobile Model
        # ------------------------
        try:
            mobile_results = mobile_model(frame)
        except Exception as e:
            print("Mobile detection error:", e)
            mobile_results = []

        mobile_detected = False
        for result in mobile_results:
            if result.boxes is not None:
                for box in result.boxes:
                    if int(box.cls) == 67:  # Class 67 represents mobile phone
                        mobile_detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # Draw an orange rectangle and label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                        cv2.putText(frame, "Mobile", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        # Update state for mobile detection
        if mobile_detected:
            if not mobile_in_progress:
                mobile_in_progress = True
                mobile_frames = 1
                if not mobile_recording:
                    mobile_recording = True
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    mobile_video = cv2.VideoWriter("output_mobiledetection.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            else:
                mobile_frames += 1
            cv2.putText(frame, ACTION_NAME + "!", (850, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            if mobile_recording and mobile_video:
                mobile_video.write(frame)
        else:
            if mobile_in_progress:
                mobile_in_progress = False
                if mobile_frames >= MOBILE_THRESHOLD:
                    if mobile_recording and mobile_video:
                        mobile_video.release()
                    now_save = datetime.now()
                    timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                    proof_filename = f"output_mobiledetection_{timestamp}.mp4"
                    date_db = now_save.date().isoformat()
                    time_db = now_save.time().strftime('%H:%M:%S')
                    cursor.execute(
                        "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                        (LECTURE_HALL_NAME, BUILDING)
                    )
                    hall_result = cursor.fetchone()
                    hall_id = hall_result[0] if hall_result else None
                    local_temp = "output_mobiledetection.mp4"
                    dest_path = os.path.join(MEDIA_DIR, proof_filename)
                    shutil.copy(local_temp, dest_path)
                    if IS_CLIENT:
                        remote_dest = f"./DetectSus/media/{proof_filename}"
                        scp.put(local_temp, remote_dest)
                    sql = """
                        INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    values = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
                    cursor.execute(sql, values)
                    db.commit()
                else:
                    if mobile_recording and mobile_video:
                        mobile_video.release()
                    if os.path.exists("output_mobiledetection.mp4"):
                        os.remove("output_mobiledetection.mp4")
                mobile_frames = 0
                mobile_recording = False
                mobile_video = None

        # ------------------------
        # Display and Key Check
        # ------------------------
        cv2.imshow("Exam Monitoring - Merged", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("Received keybaord interrupt; shutting down...")
 
finally:
    # Cleanup
    cap.release()
    if turning_recording and turning_video:
        turning_video.release()
    if mobile_recording and mobile_video:
        mobile_video.release()
    if IS_CLIENT:
        scp.close()
        ssh.close()
    cv2.destroyAllWindows()
