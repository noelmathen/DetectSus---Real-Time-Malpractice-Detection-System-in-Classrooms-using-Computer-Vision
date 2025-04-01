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
MOBILE_MODEL_PATH = "yolo11m.pt"
MEDIA_DIR = "../media/"

# Thresholds for finalizing each action
TURNING_BACK_THRESHOLD = 10
HAND_RAISE_THRESHOLD = 5
MOBILE_THRESHOLD = 3
LEANING_THRESHOLD = 3
PASSING_THRESHOLD = 3

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

def calculate_distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))

def detect_passing_paper(wrists):
    threshold = 130
    min_self_wrist_dist = 100
    max_vertical_diff = 100
    close_pairs = []
    detected = False
    for i in range(len(wrists)):
        host = wrists[i]
        if calculate_distance(*host) < min_self_wrist_dist:
            continue
        for j in range(i+1, len(wrists)):
            other = wrists[j]
            pairs = [(host[0], other[0], (0, 0)), (host[0], other[1], (0, 1)),
                     (host[1], other[0], (1, 0)), (host[1], other[1], (1, 1))]
            for w1, w2, ids in pairs:
                if w1[0] == 0.0 or w2[0] == 0.0 or abs(w1[1] - w2[1]) > max_vertical_diff:
                    continue
                if calculate_distance(w1, w2) < threshold:
                    close_pairs.append((i, j, *ids))
                    detected = True
    return detected, close_pairs

def is_leaning(kp):
    if len(kp) < 7: return False
    nose, l_eye, r_eye, l_ear, r_ear, l_sh, r_sh = kp[:7]
    if any(pt is None for pt in [nose, l_eye, r_eye, l_ear, r_ear, l_sh, r_sh]): return False
    eye_dist = abs(l_eye[0] - r_eye[0])
    shoulder_dist = abs(l_sh[0] - r_sh[0])
    shoulder_height_diff = abs(l_sh[1] - r_sh[1])
    head_center = (l_eye[0] + r_eye[0]) / 2
    shoulder_center = (l_sh[0] + r_sh[0]) / 2
    if eye_dist > 0.35 * shoulder_dist or shoulder_height_diff > 40: return False
    return abs(head_center - shoulder_center) > 60

# ========================
# LOAD MODELS / CAPTURE
# ========================
pose_model = YOLO(POSE_MODEL_PATH)
mobile_model = YOLO(MOBILE_MODEL_PATH)
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ========================
# PER-ACTION TRACKING VARIABLES
# ========================
# Top-Corner (Turning Back and Hand Raise)
turn_malpractice = 0
turn_video_ctrl = 0
turn_out = None

hand_malpractice = 0
hand_video_ctrl = 0
hand_out = None

# Mobile Phone Detection
phone_in_progress = False
phone_frames = 0
video_control = False
out_mobile = None

# Front (Leaning and Passing Paper)
mal_leans, vc_lean, out_lean = 0, 0, None
mal_passes, vc_pass, out_pass = 0, 0, None

# ========================
# MAIN LOOP
# ========================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # -------------
    # Date/Time + Lecture Hall Overlay (Top-Left)
    # -------------
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
    hall_text = f"{LECTURE_HALL_NAME} | {BUILDING}"
    cv2.putText(frame, hall_text, (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Initialize flags and lists for detections
    turn_in_frame = False
    hand_in_frame = False
    all_keypoints = []
    wrists = []

    # -----------------------
    # Pose Model Inference (for Turning, Hand Raise, Leaning & Passing Paper)
    # -----------------------
    pose_results = pose_model(frame)
    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []
        for kp in keypoints:
            all_keypoints.append(kp)
            if len(kp) >= 11:
                wrists.append([kp[9], kp[10]])
            # Top-Corner detections:
            turning = is_turning_back(kp)
            hraise = is_hand_raised(kp)

            if turning:
                turn_in_frame = True
                turn_malpractice += 1
            if hraise:
                hand_in_frame = True
                hand_malpractice += 1

            # Draw keypoints for turning/back and hand raise (as in top_corner.py)
            # Priority: turning back => red, else if hand raise => blue, else => green
            if turning:
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)  # Red for Turning Back
            elif hraise:
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)  # Blue for Hand Raise
            else:
                for x, y in kp[:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            if len(kp) > 11:
                for x, y in kp[11:]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

    # -----------------------
    # Front Camera Inference (Leaning & Passing Paper)
    # -----------------------
    pass_detected, close_pairs = detect_passing_paper(wrists)
    red_wrist_set = {(i, w) for i, j, wi, wj in close_pairs for (i, w) in [(i, wi), (j, wj)]}
    any_lean = False
    for idx, kp in enumerate(all_keypoints):
        lean_flag = is_leaning(kp)
        for i, (x, y) in enumerate(kp):
            # For wrists used in passing paper detection, use Brown color
            if (idx, i - 9) in red_wrist_set and i in [9, 10]:
                cv2.circle(frame, (int(x), int(y)), 5, (42, 42, 165), -1)  # Brown for Passing Paper
            # For leaning, use Purple for keypoints (first 6 points)
            elif lean_flag and i < 6:
                cv2.circle(frame, (int(x), int(y)), 5, (128, 0, 128), -1)  # Purple for Leaning
            else:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
        if lean_flag:
            any_lean = True

    # -----------------------
    # Mobile Phone Detection Inference
    # -----------------------
    mobile_results = mobile_model(frame)
    mobile_detected = False
    for result in mobile_results:
        if result.boxes is not None:
            for box in result.boxes:
                if int(box.cls) == 67:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    mobile_detected = True
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 105, 255), 2)  # Pink rectangle
                    cv2.putText(frame, "Mobile", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 105, 255), 2)

    # -----------------------
    # Stacked Message Writing (Top-Right)
    # -----------------------
    detection_messages = []
    if turn_in_frame:
        detection_messages.append(("Turning Back!", (0, 0, 255)))  # Red
    if hand_in_frame:
        detection_messages.append(("Hand Raised!", (255, 0, 0)))     # Blue
    if any_lean:
        detection_messages.append(("Leaning!", (128, 0, 128)))       # Purple
    if pass_detected:
        detection_messages.append(("Passing Paper!", (42, 42, 165)))   # Brown
    if mobile_detected:
        detection_messages.append(("Mobile Phone Detected!", (180, 105, 255)))  # Pink

    msg_x = 850
    msg_y = 100
    line_spacing = 40
    for msg, color in detection_messages:
        cv2.putText(frame, msg, (msg_x, msg_y), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        msg_y += line_spacing

    # -----------------------
    # TURNING-BACK RECORDING (Top-Corner)
    # -----------------------
    if turn_malpractice >= 1:
        if turn_video_ctrl == 0:
            turn_video_ctrl = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            turn_out = cv2.VideoWriter("output_turningback.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        turn_out.write(frame)
    if not turn_in_frame:
        if turn_malpractice >= TURNING_BACK_THRESHOLD:
            if turn_video_ctrl == 1 and turn_out is not None:
                turn_out.release()
            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')
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

    # -----------------------
    # HAND-RAISE RECORDING (Top-Corner)
    # -----------------------
    if hand_malpractice >= 1:
        if hand_video_ctrl == 0:
            hand_video_ctrl = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            hand_out = cv2.VideoWriter("output_handraise.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        hand_out.write(frame)
    if not hand_in_frame:
        if hand_malpractice >= HAND_RAISE_THRESHOLD:
            if hand_video_ctrl == 1 and hand_out is not None:
                hand_out.release()
            now_save = datetime.now()
            date_db = now_save.date().isoformat()
            time_db = now_save.time().strftime('%H:%M:%S')
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

    # -----------------------
    # MOBILE PHONE DETECTION RECORDING
    # -----------------------
    if mobile_detected:
        if not phone_in_progress:
            phone_in_progress = True
            phone_frames = 1
            if not video_control:
                video_control = True
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out_mobile = cv2.VideoWriter("output_mobiledetection.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
        else:
            phone_frames += 1
        if video_control and out_mobile is not None:
            out_mobile.write(frame)
    else:
        if phone_in_progress:
            phone_in_progress = False
            if phone_frames >= MOBILE_THRESHOLD:
                if video_control and out_mobile is not None:
                    out_mobile.release()
                now_save = datetime.now()
                date_db = now_save.date().isoformat()
                time_db = now_save.time().strftime('%H:%M:%S')
                cursor.execute(
                    "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                    (LECTURE_HALL_NAME, BUILDING)
                )
                hall_result = cursor.fetchone()
                hall_id = hall_result[0] if hall_result else None
                timestamp = now_save.strftime("%Y-%m-%d_%H-%M-%S")
                proof_filename = f"output_{timestamp}.mp4"
                destination_path = os.path.join(MEDIA_DIR, proof_filename)
                shutil.copy("output_mobiledetection.mp4", destination_path)
                if IS_CLIENT:
                    scp.put("output_mobiledetection.mp4", destination_path)
                sql = """
                    INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                values = (date_db, time_db, "Mobile Phone Detected", proof_filename, hall_id)
                cursor.execute(sql, values)
                db.commit()
            else:
                if video_control and out_mobile is not None:
                    out_mobile.release()
                if os.path.exists("output_mobiledetection.mp4"):
                    os.remove("output_mobiledetection.mp4")
            phone_frames = 0
            video_control = False
            out_mobile = None

    # -----------------------
    # LEANING RECORDING (Front)
    # -----------------------
    if any_lean:
        mal_leans += 1
        if vc_lean == 0:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_lean = cv2.VideoWriter("output_leaning.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            vc_lean = 1
        out_lean.write(frame)
    if not any_lean and mal_leans >= LEANING_THRESHOLD:
        if vc_lean:
            out_lean.release()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            proof = f"output_{timestamp}.mp4"
            shutil.copy("output_leaning.mp4", os.path.join(MEDIA_DIR, proof))
            cursor.execute("SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                           (LECTURE_HALL_NAME, BUILDING))
            hall_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id) VALUES (%s,%s,%s,%s,%s)",
                           (now.date().isoformat(), now.time().strftime('%H:%M:%S'), "Leaning", proof, hall_id))
            db.commit()
        mal_leans, vc_lean = 0, 0

    # -----------------------
    # PASSING PAPER RECORDING (Front)
    # -----------------------
    if pass_detected:
        mal_passes += 1
        if vc_pass == 0:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out_pass = cv2.VideoWriter("output_passingpaper.mp4", fourcc, 30, (FRAME_WIDTH, FRAME_HEIGHT))
            vc_pass = 1
        out_pass.write(frame)
    if not pass_detected and mal_passes >= PASSING_THRESHOLD:
        if vc_pass:
            out_pass.release()
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            proof = f"output_{timestamp}.mp4"
            shutil.copy("output_passingpaper.mp4", os.path.join(MEDIA_DIR, proof))
            cursor.execute("SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                           (LECTURE_HALL_NAME, BUILDING))
            hall_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id) VALUES (%s,%s,%s,%s,%s)",
                           (now.date().isoformat(), now.time().strftime('%H:%M:%S'), "Passing Paper", proof, hall_id))
            db.commit()
        mal_passes, vc_pass = 0, 0

    # -----------------------
    # SHOW FRAME AND CHECK FOR EXIT
    # -----------------------
    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if turn_video_ctrl == 1 and turn_out is not None:
    turn_out.release()
if hand_video_ctrl == 1 and hand_out is not None:
    hand_out.release()
if video_control and out_mobile is not None:
    out_mobile.release()
if vc_lean and out_lean is not None:
    out_lean.release()
if vc_pass and out_pass is not None:
    out_pass.release()

if IS_CLIENT:
    scp.close()
    ssh.close()

cv2.destroyAllWindows()
