#top_corner.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running as client, import paramiko + scp
IS_CLIENT = False  # Change to True if you're on the client

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = True
CAMERA_INDEX = 0
VIDEO_PATH = "test_videos/Top_Corner.mp4"

LECTURE_HALL_NAME = "LH1"
BUILDING = "Main Building"

DB_USER = "root"
DB_PASSWORD = "Detectsus1234"
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"  # Where the final proof files go

# Thresholds for consecutive frames
TURNING_THRESHOLD = 10
HAND_RAISE_THRESHOLD = 5

# The DB table will store distinct action strings
TURNING_BACK_ACTION = "Turning Back"
HAND_RAISE_ACTION = "Hand Raised"
# ========================

# ========================
# SSH CONFIG (Only if client)
# ========================
if IS_CLIENT:
    hostname = "192.168.39.44"
    username = "allen"
    password_ssh = "5321"

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

# ========================
# UTILITY FUNCTIONS
# ========================
def is_turning_back(kp):
    """
    Basic check for turning back using nose, eyes, ears, shoulders.
    """
    if kp is None or len(kp) < 7:
        return False

    nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder = kp[:7]
    if any(pt is None for pt in [nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder]):
        return False

    eye_dist = abs(l_eye[0] - r_eye[0])
    shoulder_dist = abs(l_shoulder[0] - r_shoulder[0])
    return (eye_dist < 0.4 * shoulder_dist
            and l_ear[0] > l_eye[0]
            and r_ear[0] < r_eye[0])

def is_hand_raised(kp):
    """
    Basic check for hand raise using shoulders, elbows, wrists => indices 5..10.
    """
    if kp is None or len(kp) < 11:
        return False

    l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist = kp[5:11]
    if any(pt is None for pt in [l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist]):
        return False

    threshold = min(l_shoulder[1], r_shoulder[1]) + 30
    return (l_wrist[1] < threshold) or (r_wrist[1] < threshold)

# ========================
# MALPRACTICE STATE
# ========================
turning_in_progress = False
turning_frames = 0
turning_video = None
turning_recording = False

hand_in_progress = False
hand_frames = 0
hand_video = None
hand_recording = False

# ========================
# MAIN LOOP
# ========================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # 1) Overlays for date/time + lecture hall
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')  # 12-hour
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(frame, overlay_text, (50, 100),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)

    hall_text = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, hall_text, (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # 2) YOLO Pose inference
    results = pose_model(frame)

    # We'll track whether we saw turning or hand-raise in the current frame
    turning_this_frame = False
    hand_this_frame = False

    # For coloring keypoints, we do multiple passes
    for result in results:
        keypoints_arr = result.keypoints.xy.cpu().numpy() if result.keypoints else []

        for kp in keypoints_arr:
            # 2a) Check turning
            if is_turning_back(kp):
                turning_this_frame = True
                # Mark 1..6 keypoints => red
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
            else:
                # Mark them green if not turning
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # 2b) Check hand raise
            if is_hand_raised(kp) and not turning_this_frame:
                # We only color them blue if not turning (since turning has priority for those same points).
                hand_this_frame = True
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)
            else:
                # Mark them green if no hand raise
                # but only if we haven't marked them red for turning
                if not turning_this_frame:
                    for x, y in kp[6:11]:
                        cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # Additional keypoints (beyond 11)
            # We'll keep them green if not turning, not hand-raise, etc.
            # If turning or hand raise => we haven't changed them, so let's keep them green
            for x, y in kp[11:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

    # 3) Update turning_in_progress
    if turning_this_frame:
        if not turning_in_progress:
            turning_in_progress = True
            turning_frames = 1
            # Start recording if not already
            if not turning_recording:
                turning_recording = True
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                turning_video = cv2.VideoWriter("output_turningback.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        else:
            turning_frames += 1

        # Red message top-right
        cv2.putText(frame, TURNING_BACK_ACTION + "!", (850, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    else:
        # If we had a turning event, finalize if threshold is met
        if turning_in_progress:
            turning_in_progress = False
            if turning_frames >= TURNING_THRESHOLD:
                # Finalize => rename, DB log
                if turning_recording and turning_video:
                    turning_video.release()

                now_save = datetime.now()
                date_db = now_save.date().isoformat()
                time_db = now_save.time().strftime('%H:%M:%S')

                # Lecture hall ID
                cursor.execute(
                    "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                    (LECTURE_HALL_NAME, BUILDING)
                )
                hall_result = cursor.fetchone()
                hall_id = hall_result[0] if hall_result else None

                timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                proof_filename = f"output_turningback_{timestamp}.mp4"
                local_temp = "output_turningback.mp4"
                dest_path = os.path.join(MEDIA_DIR, proof_filename)
                shutil.copy(local_temp, dest_path)

                if IS_CLIENT:
                    remote_dest = f"./DetectSus/media/{proof_filename}"
                    scp.put(local_temp, remote_dest)

                # DB insert
                sql = """
                    INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (date_db, time_db, TURNING_BACK_ACTION, proof_filename, hall_id)
                cursor.execute(sql, values)
                db.commit()
            else:
                # Not enough frames => discard
                if turning_recording and turning_video:
                    turning_video.release()
                if os.path.exists("output_turningback.mp4"):
                    os.remove("output_turningback.mp4")

            turning_frames = 0
            turning_recording = False
            turning_video = None

    # 4) Update hand_in_progress
    if hand_this_frame:
        if not hand_in_progress:
            hand_in_progress = True
            hand_frames = 1
            if not hand_recording:
                hand_recording = True
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                hand_video = cv2.VideoWriter("output_handraise.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        else:
            hand_frames += 1

        # Blue message below turning's line => (850, 150)
        cv2.putText(frame, HAND_RAISE_ACTION + "!", (850, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
    else:
        # No hand in this frame => finalize if threshold is reached
        if hand_in_progress:
            hand_in_progress = False
            if hand_frames >= HAND_RAISE_THRESHOLD:
                if hand_recording and hand_video:
                    hand_video.release()

                now_save = datetime.now()
                date_db = now_save.date().isoformat()
                time_db = now_save.time().strftime('%H:%M:%S')

                # Lecture hall ID
                cursor.execute(
                    "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                    (LECTURE_HALL_NAME, BUILDING)
                )
                hall_result = cursor.fetchone()
                hall_id = hall_result[0] if hall_result else None

                timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                proof_filename = f"output_handraise_{timestamp}.mp4"
                local_temp = "output_handraise.mp4"
                dest_path = os.path.join(MEDIA_DIR, proof_filename)
                shutil.copy(local_temp, dest_path)

                if IS_CLIENT:
                    remote_dest = f"./DetectSus/media/{proof_filename}"
                    scp.put(local_temp, remote_dest)

                # DB insert
                sql = """
                    INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (date_db, time_db, HAND_RAISE_ACTION, proof_filename, hall_id)
                cursor.execute(sql, values)
                db.commit()
            else:
                # Not enough frames => discard
                if hand_recording and hand_video:
                    hand_video.release()
                if os.path.exists("output_handraise.mp4"):
                    os.remove("output_handraise.mp4")

            hand_frames = 0
            hand_recording = False
            hand_video = None

    # If we are currently recording turning or hand, write frames
    if turning_in_progress and turning_recording and turning_video:
        turning_video.write(frame)

    if hand_in_progress and hand_recording and hand_video:
        hand_video.write(frame)

    cv2.imshow("Exam Monitoring - Merged", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if turning_recording and turning_video:
    turning_video.release()
if hand_recording and hand_video:
    hand_video.release()

if IS_CLIENT:
    scp.close()
    ssh.close()

cv2.destroyAllWindows()
