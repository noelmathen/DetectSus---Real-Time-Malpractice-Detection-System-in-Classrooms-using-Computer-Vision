# front.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# If running on the client, import paramiko + scp
IS_CLIENT = True  # Change to True on client, False on host

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# ========================
# CONFIGURABLE VARIABLES
# ========================
USE_CAMERA = True
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Front.mp4"
# VIDEO_PATH = "test_videos/Passing_Paper.mp4"
# VIDEO_PATH = "test_videos/Phone_2.mp4"

LECTURE_HALL_NAME = "Hall-1, Block A"
BUILDING = "PG Block"

DB_USER = "root"
DB_PASSWORD = "Detectsus1234"
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Pose model for leaning and passing detection
POSE_MODEL_PATH = "yolov8n-pose.pt"
# Mobile model (for mobile phone detection)
MOBILE_MODEL_PATH = "yolo11n.pt"

MEDIA_DIR = "../media/"

# Thresholds for events
LEANING_THRESHOLD = 3      # consecutive frames needed for leaning
PASSING_THRESHOLD = 3      # consecutive frames needed for passing paper
MOBILE_THRESHOLD = 3       # consecutive frames needed for mobile phone detection

# Action strings
LEANING_ACTION = "Leaning"
PASSING_ACTION = "Passing Paper"
ACTION_MOBILE = "Mobile Phone Detected"

# ========================
# SSH CONFIG (Only if client)
# ========================
if IS_CLIENT:
    hostname = "192.168.1.3"
    username = "allen"
    password_ssh = "5321"

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
    # Local DB if host
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
def is_leaning(keypoints):
    """
    Improved leaning detection by comparing head & shoulder centers.
    """
    if keypoints is None or len(keypoints) < 7:
        return False

    nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder = keypoints[:7]
    if any(pt is None for pt in [nose, l_eye, r_eye, l_ear, r_ear, l_shoulder, r_shoulder]):
        return False

    eye_dist = abs(l_eye[0] - r_eye[0])
    shoulder_dist = abs(l_shoulder[0] - r_shoulder[0])
    shoulder_height_diff = abs(l_shoulder[1] - r_shoulder[1])
    head_center_x = (l_eye[0] + r_eye[0]) / 2
    shoulder_center_x = (l_shoulder[0] + r_shoulder[0]) / 2

    if eye_dist > 0.35 * shoulder_dist:
        return False
    if shoulder_height_diff > 40:
        return False

    return abs(head_center_x - shoulder_center_x) > 60

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(np.array(p1) - np.array(p2))

def detect_passing_paper(wrists):
    """
    If any pair of wrists from different people is below threshold => passing paper.
    """
    threshold = 130
    min_self_wrist_dist = 100
    max_vertical_diff = 100

    close_pairs = []
    passing_detected = False

    for i in range(len(wrists)):
        host = wrists[i]
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
# LOAD MODELS
# ========================
pose_model = YOLO(POSE_MODEL_PATH)
mobile_model = YOLO(MOBILE_MODEL_PATH)

# ========================
# VIDEO SOURCE
# ========================
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# PER-EVENT STATE VARIABLES
# ========================
# Leaning detection states
lean_in_progress = False
lean_frames = 0
lean_recording = False
lean_video = None

# Passing paper detection states
passing_in_progress = False
passing_frames = 0
passing_recording = False
passing_video = None

# Mobile phone detection states
mobile_in_progress = False
mobile_frames = 0
mobile_recording = False
mobile_video = None

# ========================
# MAIN LOOP
# ========================
    
try:  
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        # Overlay: date/time and lecture hall info
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
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (255,255,255), 2, cv2.LINE_AA)
        hall_text = f"{LECTURE_HALL_NAME} | {BUILDING}"
        cv2.putText(frame, hall_text, (50, FRAME_HEIGHT - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2, cv2.LINE_AA)

        # YOLO pose inference for leaning & passing paper
        results = pose_model(frame)

        # 1) Leaning Detection (process each person's keypoints)
        leaning_this_frame = False
        # 2) Passing Paper Detection: collect wrists and keypoints for coloring later
        passing_this_frame = False
        wrist_positions = []
        all_keypoints = []

        for r in results:
            kpts = r.keypoints.xy.cpu().numpy() if r.keypoints else []
            if len(kpts) > 0:
                all_keypoints.append(kpts)
                # For passing detection, collect wrists (expecting at least 11 keypoints)
                for kp in kpts:
                    if len(kp) >= 11:
                        wrist_positions.append([kp[9], kp[10]])

        passing_detected, close_pairs = detect_passing_paper(wrist_positions)
        if passing_detected:
            passing_this_frame = True

        # Separate pass for leaning detection
        for r in results:
            kpts = r.keypoints.xy.cpu().numpy() if r.keypoints else []
            for kp in kpts:
                if is_leaning(kp):
                    leaning_this_frame = True

        # 3) Color and draw keypoints for leaning/passing
        red_color = (0, 0, 255)
        blue_color = (255, 0, 0)
        green_color = (0, 255, 0)

        # Build a set for passing wrists
        passing_wrist_set = set()
        for (i, j, hw_idx, w_idx) in close_pairs:
            passing_wrist_set.add((i, hw_idx))
            passing_wrist_set.add((j, w_idx))

        person_index = 0
        for kpts in all_keypoints:
            for kp in kpts:
                if is_leaning(kp):
                    for x, y in kp[:6]:
                        cv2.circle(frame, (int(x), int(y)), 5, red_color, -1)
                else:
                    for x, y in kp[:6]:
                        cv2.circle(frame, (int(x), int(y)), 5, green_color, -1)
                if len(kp) >= 11:
                    lx, ly = kp[9]
                    rx, ry = kp[10]
                    if (person_index, 0) in passing_wrist_set:
                        cv2.circle(frame, (int(lx), int(ly)), 5, blue_color, -1)
                    else:
                        cv2.circle(frame, (int(lx), int(ly)), 5, green_color, -1)
                    if (person_index, 1) in passing_wrist_set:
                        cv2.circle(frame, (int(rx), int(ry)), 5, blue_color, -1)
                    else:
                        cv2.circle(frame, (int(rx), int(ry)), 5, green_color, -1)
                for x, y in kp[11:]:
                    cv2.circle(frame, (int(x), int(y)), 5, green_color, -1)
                person_index += 1

        # Draw text for leaning and passing detection
        if leaning_this_frame:
            cv2.putText(frame, LEANING_ACTION + "!", (850, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, red_color, 3)
        if passing_this_frame:
            cv2.putText(frame, PASSING_ACTION + "!", (850, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, blue_color, 3)

        # 4) Update leaning event states
        if leaning_this_frame:
            if not lean_in_progress:
                lean_in_progress = True
                lean_frames = 1
                if not lean_recording:
                    lean_recording = True
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    lean_video = cv2.VideoWriter("output_leaning.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            else:
                lean_frames += 1
        else:
            if lean_in_progress:
                lean_in_progress = False
                if lean_frames >= LEANING_THRESHOLD:
                    if lean_recording and lean_video:
                        lean_video.release()
                    now_save = datetime.now()
                    date_db = now_save.date().isoformat()
                    time_db = now_save.time().strftime('%H:%M:%S')
                    cursor.execute(
                        "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                        (LECTURE_HALL_NAME, BUILDING)
                    )
                    row = cursor.fetchone()
                    hall_id = row[0] if row else None
                    timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                    local_temp = "output_leaning.mp4"
                    proof_filename = f"output_leaning_{timestamp}.mp4"
                    dest_path = os.path.join(MEDIA_DIR, proof_filename)
                    shutil.copy(local_temp, dest_path)
                    if IS_CLIENT:
                        remote_dest = f"./DetectSus/media/{proof_filename}"
                        scp.put(local_temp, remote_dest)
                    sql = """
                        INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    val = (date_db, time_db, LEANING_ACTION, proof_filename, hall_id)
                    cursor.execute(sql, val)
                    db.commit()
                else:
                    if lean_recording and lean_video:
                        lean_video.release()
                    if os.path.exists("output_leaning.mp4"):
                        os.remove("output_leaning.mp4")
                lean_frames = 0
                lean_recording = False
                lean_video = None

        if lean_in_progress and lean_recording and lean_video:
            lean_video.write(frame)

        # 5) Update passing paper event states
        if passing_this_frame:
            if not passing_in_progress:
                passing_in_progress = True
                passing_frames = 1
                if not passing_recording:
                    passing_recording = True
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    passing_video = cv2.VideoWriter("output_passingpaper.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            else:
                passing_frames += 1
        else:
            if passing_in_progress:
                passing_in_progress = False
                if passing_frames >= PASSING_THRESHOLD:
                    if passing_recording and passing_video:
                        passing_video.release()
                    now_save = datetime.now()
                    date_db = now_save.date().isoformat()
                    time_db = now_save.time().strftime('%H:%M:%S')
                    cursor.execute(
                        "SELECT id FROM app_lecturehall WHERE hall_name=%s AND building=%s LIMIT 1",
                        (LECTURE_HALL_NAME, BUILDING)
                    )
                    row = cursor.fetchone()
                    hall_id = row[0] if row else None
                    timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                    local_temp = "output_passingpaper.mp4"
                    proof_filename = f"output_passingpaper_{timestamp}.mp4"
                    dest_path = os.path.join(MEDIA_DIR, proof_filename)
                    shutil.copy(local_temp, dest_path)
                    if IS_CLIENT:
                        remote_dest = f"./DetectSus/media/{proof_filename}"
                        scp.put(local_temp, remote_dest)
                    sql = """
                        INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    val = (date_db, time_db, PASSING_ACTION, proof_filename, hall_id)
                    cursor.execute(sql, val)
                    db.commit()
                else:
                    if passing_recording and passing_video:
                        passing_video.release()
                    if os.path.exists("output_passingpaper.mp4"):
                        os.remove("output_passingpaper.mp4")
                passing_frames = 0
                passing_recording = False
                passing_video = None

        if passing_in_progress and passing_recording and passing_video:
            passing_video.write(frame)

        # 6) MOBILE PHONE DETECTION
        try:
            mobile_results = mobile_model(frame)
        except Exception as e:
            print("Mobile detection error:", e)
            mobile_results = []
        mobile_detected = False
        # Look through detection boxes for mobile (class 67)
        for m_res in mobile_results:
            if m_res.boxes is not None:
                for box in m_res.boxes:
                    if int(box.cls) == 67:
                        mobile_detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        # Draw orange rectangle and label for mobile detection
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,165,255), 2)
                        cv2.putText(frame, "Mobile", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,165,255), 2)
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
            cv2.putText(frame, ACTION_MOBILE + "!", (850, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,165,255), 3)
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
                    row = cursor.fetchone()
                    hall_id = row[0] if row else None
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
                    val = (date_db, time_db, ACTION_MOBILE, proof_filename, hall_id)
                    cursor.execute(sql, val)
                    db.commit()
                else:
                    if mobile_recording and mobile_video:
                        mobile_video.release()
                    if os.path.exists("output_mobiledetection.mp4"):
                        os.remove("output_mobiledetection.mp4")
                mobile_frames = 0
                mobile_recording = False
                mobile_video = None

        # 7) Display the frame and check for quit key
        cv2.imshow("Exam Monitoring - Merged Leaning, Passing & Mobile", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("Received keybaord interrupt; shutting down...")
 
finally:
    # Cleanup
    cap.release()
    if lean_recording and lean_video:
        lean_video.release()
    if passing_recording and passing_video:
        passing_video.release()
    if mobile_recording and mobile_video:
        mobile_video.release()
    if IS_CLIENT:
        scp.close()
        ssh.close()
    cv2.destroyAllWindows()
