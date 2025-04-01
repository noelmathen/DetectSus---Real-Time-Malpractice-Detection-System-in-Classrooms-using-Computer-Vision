#top_corner.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running as client, use Paramiko + SCP for SSH connection
IS_CLIENT = False

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
BUILDING = "Main Building"

# Common DB credentials
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"

# Thresholds for finalizing each action
TURNING_BACK_THRESHOLD = 10
HAND_RAISE_THRESHOLD = 5

# ========================
# SSH / DB Config
# ========================
if IS_CLIENT:
    hostname = "192.168.147.145"  # Host system IP
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    # SSH connection setup
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)

    # SCP connection setup
    scp = SCPClient(ssh.get_transport())

    # Remote DB connection from client
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
# HELPER FUNCTIONS
# ========================
def is_turning_back(kp):
    """Check if student is turning back using the first 7 keypoints (nose, eyes, ears, shoulders)."""
    if kp is None or len(kp) < 7:
        return False

    nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder = kp[:7]
    if any(pt is None for pt in [nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder]):
        return False

    eye_dist = abs(l_eye[0] - r_eye[0])
    shoulder_dist = abs(l_shoulder[0] - r_shoulder[0])
    return eye_dist < 0.4 * shoulder_dist and l_ear[0] > l_eye[0] and r_ear[0] < r_eye[0]

def is_hand_raised(kp):
    """
    Detect if a student is raising their hand based on keypoint positions:
    We check the region 5:11 => (Shoulders, Elbows, Wrists).
    """
    if kp is None or len(kp) < 11:
        return False

    l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist = kp[5:11]
    if any(pt is None for pt in [l_shoulder, r_shoulder, l_elbow, r_elbow, l_wrist, r_wrist]):
        return False

    threshold = min(l_shoulder[1], r_shoulder[1]) + 30

    # If either wrist is above shoulders
    if l_wrist[1] < threshold or r_wrist[1] < threshold:
        return True
    return False

# ========================
# LOAD MODEL / CAPTURE
# ========================
pose_model = YOLO(POSE_MODEL_PATH)
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# PER-ACTION TRACKING
# ========================
turn_malpractice = 0
turn_video_ctrl = 0

hand_malpractice = 0
hand_video_ctrl = 0

turn_out = None
hand_out = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    pose_results = pose_model(frame)

    # -------------
    # Date/Time + Lecture Hall Overlay
    # -------------
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')  # 12-hour format
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

    # Flags if we saw turning or hand raise in this frame
    turn_in_frame = False
    hand_in_frame = False

    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []
        for kp in keypoints:
            # 1) Check turning
            turning = is_turning_back(kp)
            # 2) Check hand raise
            hraise = is_hand_raised(kp)

            if turning:
                turn_in_frame = True
                turn_malpractice += 1
            if hraise:
                hand_in_frame = True
                hand_malpractice += 1

            # Color keypoints
            # Priority: turning back => red, else if hand raise => blue, else => green
            if turning:
                # Mark first 6 keypoints in red
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
            elif hraise:
                # Mark relevant keypoints in blue (shoulders to wrists)
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)
            else:
                # Mark these in green
                for x, y in kp[:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # Mark the rest in green
            if len(kp) > 11:
                for x, y in kp[11:]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

    # If turning in this frame => show red text up top
    if turn_in_frame:
        cv2.putText(frame, "Turning Back!", (850, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # If hand raise in this frame => show blue text slightly below turning's text
    if hand_in_frame:
        cv2.putText(frame, "Hand Raised!", (850, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

    # ================
    # TURNING-BACK RECORDING
    # ================
    if turn_malpractice >= 1:
        if turn_video_ctrl == 0:
            turn_video_ctrl = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            turn_out = cv2.VideoWriter("output_turningback.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        turn_out.write(frame)

    # If no turning => check threshold
    if not turn_in_frame:
        if turn_malpractice >= TURNING_BACK_THRESHOLD:
            # finalize turning
            if turn_video_ctrl == 1 and turn_out is not None:
                turn_out.release()
            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')

            # get hall id
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"turning_{timestamp}.mp4"
            destination_path = os.path.join(MEDIA_DIR, proof_filename)
            shutil.copy("output_turningback.mp4", destination_path)

            if IS_CLIENT:
                scp.put("output_turningback.mp4", destination_path)

            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (date_db, time_db, "Turning Back", proof_filename, hall_id)
            cursor.execute(sql, values)
            db.commit()

            turn_malpractice = 0
            turn_video_ctrl = 0
            turn_out = None
        else:
            if turn_video_ctrl == 1 and turn_out is not None:
                turn_out.release()
            turn_malpractice = 0
            turn_video_ctrl = 0
            turn_out = None

    # ================
    # HAND-RAISE RECORDING
    # ================
    if hand_malpractice >= 1:
        if hand_video_ctrl == 0:
            hand_video_ctrl = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            hand_out = cv2.VideoWriter("output_handraise.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        hand_out.write(frame)

    # If no hand raise => check threshold
    if not hand_in_frame:
        if hand_malpractice >= HAND_RAISE_THRESHOLD:
            # finalize
            if hand_video_ctrl == 1 and hand_out is not None:
                hand_out.release()
            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')

            # get hall id
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"handraise_{timestamp}.mp4"
            destination_path = os.path.join(MEDIA_DIR, proof_filename)
            shutil.copy("output_handraise.mp4", destination_path)

            if IS_CLIENT:
                scp.put("output_handraise.mp4", destination_path)

            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (date_db, time_db, "Hand Raised", proof_filename, hall_id)
            cursor.execute(sql, values)
            db.commit()

            hand_malpractice = 0
            hand_video_ctrl = 0
            hand_out = None
        else:
            if hand_video_ctrl == 1 and hand_out is not None:
                hand_out.release()
            hand_malpractice = 0
            hand_video_ctrl = 0
            hand_out = None

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()

# Release any open videos
if turn_video_ctrl == 1 and turn_out is not None:
    turn_out.release()
if hand_video_ctrl == 1 and hand_out is not None:
    hand_out.release()

if IS_CLIENT:
    scp.close()
    ssh.close()

cv2.destroyAllWindows()
