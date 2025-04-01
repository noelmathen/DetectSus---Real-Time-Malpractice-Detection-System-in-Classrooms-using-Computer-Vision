# front.py
import cv2
import os
import shutil
import numpy as np
import mysql.connector
from datetime import datetime
from ultralytics import YOLO

# SSH flag (for client)
IS_CLIENT = False

if IS_CLIENT:
    import paramiko
    from scp import SCPClient

# CONFIG
USE_CAMERA = True
CAMERA_INDEX = 1
VIDEO_PATH = "test_videos/Front.mp4"

LECTURE_HALL_NAME = "LH2"
BUILDING = "KE Block"

DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "exam_monitoring"

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

POSE_MODEL_PATH = "yolov8n-pose.pt"
MEDIA_DIR = "../media/"
LEANING_THRESHOLD = 3
PASSING_THRESHOLD = 3

# SSH setup
if IS_CLIENT:
    hostname = "192.168.147.145"
    username = "SHRUTI S"
    password_ssh = "1234shibu"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=22, username=username, password=password_ssh)
    scp = SCPClient(ssh.get_transport())

    db = mysql.connector.connect(
        host=hostname, port=3306,
        user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
else:
    db = mysql.connector.connect(
        host="localhost", user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )
cursor = db.cursor()

pose_model = YOLO(POSE_MODEL_PATH)
cap = cv2.VideoCapture(CAMERA_INDEX if USE_CAMERA else VIDEO_PATH)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# ===================== HELPERS =====================
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

# ===================== STATE =====================
mal_leans, mal_passes = 0, 0
out_lean, out_pass = None, None
vc_lean, vc_pass = 0, 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    day = now.strftime('%a')
    date = now.strftime('%d-%m-%Y')
    time_disp = now.strftime('%I:%M:%S %p').lower()
    overlay = f"{day} | {date} | {time_disp}"
    cv2.putText(frame, overlay, (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255,255,255), 2)
    cv2.putText(frame, f"{LECTURE_HALL_NAME} | {BUILDING}", (50, FRAME_HEIGHT - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    results = pose_model(frame)
    all_keypoints, wrists = [], []

    for r in results:
        kpts = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else []
        for kp in kpts:
            all_keypoints.append(kp)
            if len(kp) >= 11:
                wrists.append([kp[9], kp[10]])

    pass_detected, close_pairs = detect_passing_paper(wrists)
    red_wrist_set = {(i, w) for i, j, wi, wj in close_pairs for (i, w) in [(i, wi), (j, wj)]}

    any_lean = False
    for idx, kp in enumerate(all_keypoints):
        is_lean = is_leaning(kp)
        color = (0, 0, 255) if is_lean else (0, 255, 0)
        for i, (x, y) in enumerate(kp):
            if (idx, i - 9) in red_wrist_set and i in [9, 10]:
                cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)  # Blue for passing paper
            elif is_lean and i < 6:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
            else:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
        if is_lean: any_lean = True

    # Show detections
    if any_lean:
        mal_leans += 1
        cv2.putText(frame, "Leaning!", (850, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        if vc_lean == 0:
            out_lean = cv2.VideoWriter("output_leaning.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 30, (FRAME_WIDTH, FRAME_HEIGHT))
            vc_lean = 1
        out_lean.write(frame)

    if pass_detected:
        mal_passes += 1
        cv2.putText(frame, "Passing Paper!", (850, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        if vc_pass == 0:
            out_pass = cv2.VideoWriter("output_passingpaper.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 30, (FRAME_WIDTH, FRAME_HEIGHT))
            vc_pass = 1
        out_pass.write(frame)

    if not any_lean and mal_leans >= LEANING_THRESHOLD:
        if vc_lean:
            out_lean.release()
            proof = f"output_{timestamp}.mp4"
            shutil.copy("output_leaning.mp4", os.path.join(MEDIA_DIR, proof))
            cursor.execute("SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1", (LECTURE_HALL_NAME, BUILDING))
            hall_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id) VALUES (%s,%s,%s,%s,%s)",
                           (now.date().isoformat(), now.time().strftime('%H:%M:%S'), "Leaning", proof, hall_id))
            db.commit()
        mal_leans, vc_lean = 0, 0

    if not pass_detected and mal_passes >= PASSING_THRESHOLD:
        if vc_pass:
            out_pass.release()
            proof = f"output_{timestamp}.mp4"
            shutil.copy("output_passingpaper.mp4", os.path.join(MEDIA_DIR, proof))
            cursor.execute("SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1", (LECTURE_HALL_NAME, BUILDING))
            hall_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id) VALUES (%s,%s,%s,%s,%s)",
                           (now.date().isoformat(), now.time().strftime('%H:%M:%S'), "Passing Paper", proof, hall_id))
            db.commit()
        mal_passes, vc_pass = 0, 0

    cv2.imshow("Exam Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
if vc_lean and out_lean: out_lean.release()
if vc_pass and out_pass: out_pass.release()
if IS_CLIENT:
    scp.close()
    ssh.close()
cv2.destroyAllWindows()
