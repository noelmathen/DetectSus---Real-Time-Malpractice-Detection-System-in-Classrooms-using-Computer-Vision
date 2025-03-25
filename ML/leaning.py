#leaning.py
from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime
import mysql.connector
import shutil
import os


# MySQL Connection
db = mysql.connector.connect(
    host="localhost",     # Change this to your MySQL host
    user="root",          # Your MySQL username
    password="",  # Your MySQL password
    database="exam_monitoring"
)
cursor = db.cursor()

# Load YOLOv8 models
pose_model = YOLO("yolov8n-pose.pt")  # For pose estimation
#object_model = YOLO("yolov8n.pt")  # For object detection (mobile phones)

# Choose between webcam or video file
use_camera = False  

if use_camera:
    cap = cv2.VideoCapture(1)  # 0 is the default webcam
else:
    video_path = "/test_videos/Front.mp4"
    cap = cv2.VideoCapture(video_path)

# Set resolution
frame_width, frame_height = 1280, 720

def is_leaning(keypoints):
    """
    Detect if a student is turning back based on keypoint positions.
    """
    if keypoints is None or len(keypoints) < 7:
        return False  # Not enough keypoints detected

    nose, left_eye, right_eye, left_ear, right_ear, left_shoulder, right_shoulder = keypoints[:7]

    if nose is None or left_eye is None or right_eye is None or left_ear is None or right_ear is None:
        return False  # Missing keypoints

    # Calculate horizontal distances
    eye_dist = abs(left_eye[0] - right_eye[0])
    shoulder_dist = abs(left_shoulder[0] - right_shoulder[0])
    
    
    # If the eye distance is small but both ears are visible, the head is turned
    if eye_dist < 0.2 * shoulder_dist and left_ear[0] > left_eye[0] and right_ear[0] < right_eye[0]:
        return True

    return False

malpractice = 0
video_control = 0


while cap.isOpened():
    lean_check = list()
    leaning_back = False
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.resize(frame, (frame_width, frame_height))

    # Run YOLOv8 Pose Model
    pose_results = pose_model(frame)


    print("Starting pose estimation")

    # Process Pose Estimation Results
    for result in pose_results:
        print("getting results")
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []

        for kp in keypoints:
            print("getting key points")


            if is_leaning(kp):
                print("Checking leaning")
                malpractice = malpractice + 1
                cv2.putText(frame, "Leaning!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
                leaning_back = True

                

            # Draw keypoints (default color green)
            if not leaning_back:
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            for x, y in kp[11:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            lean_check.append(leaning_back)

    print("malpractice:",malpractice)
    if malpractice >= 1 :
        if video_control == 0:
            print("Started video recording..")
            video_control = 1
            #Save output video
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output.mp4", fourcc, 30, (frame_width, frame_height))

        # Save and display frame
        out.write(frame)
    print("lean check:",lean_check)
    if True not in lean_check:
        print("Not leaning")
        if malpractice>=3:
            print("saving data..")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out.release()
            destination_path = f"media/malpractice_{timestamp}.mp4"
            shutil.copy("output.mp4", f"{destination_path}")
            # Insert the malpractice event into MySQL
            sql = "INSERT INTO app_malpraticedetection (time, malpractice, proof) VALUES (%s, %s, %s)"
            values = (timestamp, "Leaning", f"./{destination_path}")
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
cv2.destroyAllWindows()
