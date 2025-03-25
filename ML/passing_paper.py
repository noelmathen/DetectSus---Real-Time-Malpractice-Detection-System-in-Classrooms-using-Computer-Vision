#passing_paper.py
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
pose_model = YOLO("yolov8n-pose.pt")  # Pose estimation
#object_model = YOLO("yolov8n.pt")  # Object detection

# Load video
video_path = "/test_videos/Passing_Paper.mp4"
cap = cv2.VideoCapture(video_path)

# Set resolution
frame_width, frame_height = 1280, 720

#

def calculate_distance(p1, p2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(np.array(p1) - np.array(p2))

def detect_passing_paper(wrists):
    """Detect if any two students are passing a paper based on wrist proximity."""
    for i in range(0,len(wrists)):
        host = wrists[i]
        for j in range(0,len(wrists)):
            if i==j:
                continue
            wrist1, wrist2 = wrists[j][0], wrists[j][1]
            host_wrist1, host_wrist2 = host[0], host[1]

            threshold = 100

            print(host_wrist1)

            if host_wrist1[0] != 0.0 and host_wrist1[1] != 0.0 and wrist1[0] != 0 and wrist1[1] != 0:
                distance1  = calculate_distance(host_wrist1, wrist1)
            else:
                distance1 = threshold + 100
            if host_wrist1[0] != 0.0 and host_wrist1[1] != 0.0 and wrist2[0] != 0 and wrist2[1] != 0:
                distance2  = calculate_distance(host_wrist1, wrist2)
            else:
                distance2 = threshold + 100
            if host_wrist2[0] != 0.0 and host_wrist2[1] != 0.0 and wrist1[0] != 0 and wrist1[1] != 0:
                distance3  = calculate_distance(host_wrist2, wrist1)
            else:
                distance3 = threshold + 100
            if host_wrist2[0] != 0.0 and host_wrist2[1] != 0.0 and wrist2[0] != 0 and wrist2[1] != 0:
                distance4  = calculate_distance(host_wrist2, wrist2)
            else:
                distance4 = threshold + 100

            print("\n\ndistance1:",distance1)
            print("distance2:",distance2)
            print("distance3:",distance3)
            print("distance4:",distance4)
            

            #distance = calculate_distance(wrist1, wrist2)

            if distance1 < threshold or distance2 <threshold or distance3 < threshold or distance4 <threshold:  # Threshold for hand proximity
                return True  # Potential paper passing detected
    return False

malpractice = 0
video_control = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (frame_width, frame_height))

    # Run YOLOv8 Pose Model
    pose_results = pose_model(frame)

    # Run YOLOv8 Object Detection Model
    #object_results = object_model(frame)

    # Store wrist positions
    wrist_positions = []

    for result in pose_results:
        keypoints = result.keypoints.xy.cpu().numpy() if result.keypoints is not None else []

        for kp in keypoints:
            if len(kp) < 11:  # Ensure enough keypoints are detected
                continue

            left_wrist, right_wrist = kp[9], kp[10]  # Wrists

            wrist_positions.append([left_wrist,right_wrist])

            """if left_wrist is not None:
                wrist_positions.append(left_wrist)
            if right_wrist is not None:
                wrist_positions.append(right_wrist)"""

    # Detect paper passing
    passing_paper = detect_passing_paper(wrist_positions)

    # Detect objects (paper)
    #paper_detected = False

    # If hands are close and paper is detected, confirm passing papers
    if passing_paper:
        malpractice = malpractice + 1
        cv2.putText(frame, "Passing Paper!", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    else:
        if malpractice>=3:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out.release()
            destination_path = f"media/malpractice_{timestamp}.mp4"
            shutil.copy("output.mp4", f"{destination_path}")
            # Insert the malpractice event into MySQL
            sql = "INSERT INTO app_malpraticedetection (time, malpractice, proof) VALUES (%s, %s, %s)"
            values = (timestamp, "Passing Paper", f"./{destination_path}")
            cursor.execute(sql, values)
            db.commit()
            malpractice = 0
            video_control = 0
        else:
            out.release()
            malpractice = 0
            video_control = 0



    if malpractice >= 1 :
        if video_control == 0:
            video_control = 1
            #Save output video
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output.mp4", fourcc, 30, (frame_width, frame_height))
        

        # Save and display frame
        out.write(frame)


    cv2.imshow("Exam Monitoring", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
