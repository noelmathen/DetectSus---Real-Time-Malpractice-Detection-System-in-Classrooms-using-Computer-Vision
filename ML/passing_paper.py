#passing_paper.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = False  # Change to False if running on the host system

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = False
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Passing_Paper.mp4"


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
ACTION_NAME = "Passing Paper"

# Number of consecutive frames that triggers saving proof
PASS_THRESHOLD = 3
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
    # Local DB if host
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
    """
    Detect if any two students are passing a paper
    based on wrist proximity. If distance < threshold => passing.
    Returns (passing_detected, close_pairs).
    - passing_detected: bool
    - close_pairs: list of tuples (i, j, wrist_idx1, wrist_idx2)
      indicating which specific wrists are under threshold
    """
    threshold = 100
    close_pairs = []
    passing_detected = False

    for i in range(len(wrists)):
        host = wrists[i]  # e.g. [left_wrist, right_wrist]
        host_w1, host_w2 = host[0], host[1]

        for j in range(i+1, len(wrists)):
            # Avoid re-checking same pair in reverse
            other = wrists[j]  # e.g. [left_wrist, right_wrist]
            wrist1, wrist2 = other[0], other[1]

            # Distances
            dist1 = (calculate_distance(host_w1, wrist1)
                     if host_w1[0] != 0.0 and wrist1[0] != 0.0 else threshold + 100)
            dist2 = (calculate_distance(host_w1, wrist2)
                     if host_w1[0] != 0.0 and wrist2[0] != 0.0 else threshold + 100)
            dist3 = (calculate_distance(host_w2, wrist1)
                     if host_w2[0] != 0.0 and wrist1[0] != 0.0 else threshold + 100)
            dist4 = (calculate_distance(host_w2, wrist2)
                     if host_w2[0] != 0.0 and wrist2[0] != 0.0 else threshold + 100)

            for dist_val, (hw_idx, w_idx) in zip(
                [dist1, dist2, dist3, dist4],
                [(0, 0), (0, 1), (1, 0), (1, 1)]
            ):
                if dist_val < threshold:
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

    # Overlay day/date/time in top-left
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

    # YOLO Pose
    results = pose_model(frame)

    # Collect wrist positions
    wrist_positions = []
    # Keep a separate data structure for all keypoints
    all_keypoints = []  # Will store list of [ [ (x1, y1), (x2, y2), ...], [..], ... ]

    for r in results:
        kpts = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else []
        if len(kpts) == 0:
            continue
        all_keypoints.append(kpts)

        for kp in kpts:
            if len(kp) < 11:
                continue
            # wrists
            left_wrist, right_wrist = kp[9], kp[10]
            wrist_positions.append([left_wrist, right_wrist])

    # 1) Check if passing paper
    passing_paper_detected, close_pairs = detect_passing_paper(wrist_positions)

    # 2) Drawing keypoints:
    #    - By default, color them green
    #    - For wrists in close_pairs, color them red
    #    - "Passing Paper!" text on the right if triggered
    if passing_paper_detected:
        malpractice += 1
        cv2.putText(frame, ACTION_NAME + "!", (850, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    # Draw everything
    # The trick is that close_pairs references the index in wrist_positions,
    # but we need to map back to all_keypoints
    # Approach:
    # - We'll keep a set of (globalPersonIndex, wristIndex) for red coloring
    red_wrist_set = set()

    for (i, j, hw_idx, w_idx) in close_pairs:
        # i, j => indices in wrist_positions
        # but we must also find which "person" those wrists correspond to in all_keypoints
        # We'll do a simple approach: we rely on the order in which we appended them.
        # The nth "kp" in all_keypoints that had enough points to define wrists
        # matches the nth entry in wrist_positions.
        red_wrist_set.add((i, hw_idx))  # e.g. (0, 0) => left wrist of 1st person
        red_wrist_set.add((j, w_idx))   # e.g. (1, 1) => right wrist of 2nd person

    # We'll have to iterate all persons again in the same sequence we appended them
    # person_index counts how many "valid" wrist sets we've added
    person_index = 0
    for kpts in all_keypoints:
        # kpts is an array of shape (#people, #keypoints, 2)
        for kp in kpts:
            # By default, mark all keypoints green
            for x, y in kp:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            # Now highlight left_wrist or right_wrist in red if in red_wrist_set
            # This person's wrists are kp[9], kp[10]
            # If person_index is "p", then a pair might say (p, 0) => left wrist in red
            # or (p, 1) => right wrist in red
            # But only do this if the person actually has 11 keypoints
            if len(kp) >= 11:
                # left wrist => (p,0), right wrist => (p,1)
                if (person_index, 0) in red_wrist_set:
                    lx, ly = kp[9]
                    cv2.circle(frame, (int(lx), int(ly)), 5, (0, 0, 255), -1)
                if (person_index, 1) in red_wrist_set:
                    rx, ry = kp[10]
                    cv2.circle(frame, (int(rx), int(ry)), 5, (0, 0, 255), -1)

            person_index += 1

    # 3) If passing was not detected in this frame, check threshold
    if not passing_paper_detected:
        if malpractice >= PASS_THRESHOLD:
            # finalize
            if video_control == 1:
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
                scp.put("output.mp4", destination_path)

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

    # VIDEO RECORDING LOGIC
    if malpractice >= 1:
        if video_control == 0:
            video_control = 1
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        out.write(frame)

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if IS_CLIENT:
    scp.close()
    ssh.close()
cv2.destroyAllWindows()
