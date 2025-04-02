# passing_paper.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = True  # Change to True if running on the client

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = True
CAMERA_INDEX = 0
VIDEO_PATH = "test_videos/Passing_Paper.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"  # Host system media folder
ACTION_NAME = "Passing Paper"

PASS_THRESHOLD = 3  # Consecutive frames needed
# ========================

# ========================
# SSH CONFIG (Client Only)
# ========================
if IS_CLIENT:
    hostname = "192.168.53.145"
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)

    scp = SCPClient(ssh.get_transport())

    db = mysql.connector.connect(
        host=hostname, port=3306,
        user=DB_USER, password=DB_PASSWORD,
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
# YOLO LOADING
# ========================
pose_model = YOLO(POSE_MODEL_PATH)

# ========================
# VIDEO SOURCE
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# HELPER FUNCTIONS
# ========================
def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(np.array(p1) - np.array(p2))

def detect_passing_paper(wrists):
    threshold = 130
    min_self_wrist_dist = 100
    max_vertical_diff = 100

    close_pairs = []
    passing_detected = False

    for i in range(len(wrists)):
        host = wrists[i]  # [left_wrist, right_wrist]
        if calculate_distance(*host) < min_self_wrist_dist:
            continue

        for j in range(i + 1, len(wrists)):
            other = wrists[j]
            pairings = [
                (host[0], other[0], (0, 0)),
                (host[0], other[1], (0, 1)),
                (host[1], other[0], (1, 0)),
                (host[1], other[1], (1, 1))
            ]
            for w_a, w_b, (hw_idx, w_idx) in pairings:
                if w_a[0] == 0.0 or w_b[0] == 0.0:
                    continue
                if abs(w_a[1] - w_b[1]) > max_vertical_diff:
                    continue

                dist = calculate_distance(w_a, w_b)
                if dist < threshold:
                    close_pairs.append((i, j, hw_idx, w_idx))
                    passing_detected = True

    return passing_detected, close_pairs

# ========================
# MAIN LOOP
# ========================
malpractice = 0
video_control = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # Overlay day/date/time
    now = datetime.now()
    day_str = now.strftime('%a')
    date_str = now.strftime('%d-%m-%Y')
    hour_12 = now.strftime('%I')
    minute_str = now.strftime('%M')
    second_str = now.strftime('%S')
    ampm = now.strftime('%p').lower()
    time_display = f"{hour_12}:{minute_str}:{second_str} {ampm}"
    overlay_text = f"{day_str} | {date_str} | {time_display}"
    cv2.putText(frame, overlay_text, (50, 100),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    lecture_hall_name = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, lecture_hall_name, (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # YOLO Pose
    results = pose_model(frame)

    # Collect wrist positions
    wrist_positions = []
    all_keypoints = []

    for r in results:
        kpts = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else []
        if len(kpts) == 0:
            continue
        all_keypoints.append(kpts)
        for kp in kpts:
            if len(kp) >= 11:
                wrist_positions.append([kp[9], kp[10]])

    # Check passing
    passing_paper_detected, close_pairs = detect_passing_paper(wrist_positions)
    if passing_paper_detected:
        malpractice += 1
        cv2.putText(frame, ACTION_NAME + "!", (850, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Mark wrists in red
    red_wrist_set = set()
    for (i, j, hw_idx, w_idx) in close_pairs:
        red_wrist_set.add((i, hw_idx))
        red_wrist_set.add((j, w_idx))

    # Draw all keypoints in green by default
    person_index = 0
    for kpts in all_keypoints:
        for kp in kpts:
            for x, y in kp:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            # If we have at least 11 points, color wrists if in red_wrist_set
            if len(kp) >= 11:
                if (person_index, 0) in red_wrist_set:
                    lx, ly = kp[9]
                    cv2.circle(frame, (int(lx), int(ly)), 5, (0, 0, 255), -1)
                if (person_index, 1) in red_wrist_set:
                    rx, ry = kp[10]
                    cv2.circle(frame, (int(rx), int(ry)), 5, (0, 0, 255), -1)
            person_index += 1

    # If passing not detected, see if we finalize
    if not passing_paper_detected:
        if malpractice >= PASS_THRESHOLD:
            # finalize
            if video_control == 1:
                out.release()

            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')
            timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"output_{timestamp}.mp4"

            # Copy to local media folder
            local_temp = "output_passingpaper.mp4"
            local_dest = os.path.join(MEDIA_DIR, proof_filename)
            shutil.copy(local_temp, local_dest)

            # If client, scp to remote
            if IS_CLIENT:
                remote_dest = f"./Documents/Repos/DetectSus/application/application/media/{proof_filename}"
                scp.put(local_temp, remote_dest)

            # Insert into DB
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (LECTURE_HALL_NAME, BUILDING)
            )
            hall = cursor.fetchone()
            hall_id = hall[0] if hall else None

            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            val = (date_db, time_db, ACTION_NAME, proof_filename, hall_id)
            cursor.execute(sql, val)
            db.commit()

            malpractice = 0
            video_control = 0
        else:
            if video_control == 1:
                out.release()
                malpractice = 0
                video_control = 0

    # Start/continue recording
    if malpractice >= 1:
        if video_control == 0:
            video_control = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output_passingpaper.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        out.write(frame)

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if IS_CLIENT:
    scp.close()
    ssh.close()
cv2.destroyAllWindows()