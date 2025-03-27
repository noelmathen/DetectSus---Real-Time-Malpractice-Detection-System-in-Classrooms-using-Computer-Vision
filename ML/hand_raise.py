#hand_raise.py
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
#object_model = YOLO("yolov8n.pt")   # For object detection (mobile phones)

# Choose between webcam or video file
use_camera = False  

if use_camera:
    cap = cv2.VideoCapture(1)  # 0 is the default webcam
else:
    video_path = "test_videos/Top_Corner.mp4"
    cap = cv2.VideoCapture(video_path)

# Set resolution
frame_width, frame_height = 1280, 720


def is_hand_raised(keypoints):
    """
    Detect if a student is raising their hand based on keypoint positions.
    """
    if keypoints is None or len(keypoints) < 11:
        return False
    
    left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist = keypoints[5:11]
    
    #if None in [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist]:
    #    return False
    
    if left_shoulder is None or right_shoulder is None or left_elbow is None or right_elbow is None or left_wrist is None or right_wrist is None:
        return False 
    
    threshold = min(left_shoulder[1], right_shoulder[1]) + 30# Shoulder height


    if right_wrist[1] == 0.0:
        right_wrist[1] = threshold + 10

    if left_wrist[1] == 0.0:
        left_wrist[1] = threshold + 10

    #print("Threhsold:",threshold)
    #print("left_wrist:",left_wrist[1])
    #print("right_wrist:",right_wrist[1])
    if left_wrist[1] < threshold  or right_wrist[1] < threshold:  # If either wrist is above shoulders
        #print("hand raise")
        return True
    
    return False

malpractice = 0
video_control = 0


while cap.isOpened():
    hand_raised_check = list()
    hand_raised = False
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


            if is_hand_raised(kp):
                print("Checking hand raise")
                malpractice = malpractice + 1
                cv2.putText(frame, "Hand Raised!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), -1)
                hand_raised = True

                

            # Draw keypoints (default color green)
            if not hand_raised:
                for x, y in kp[6:11]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            for x, y in kp[11:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            for x, y in kp[:6]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            hand_raised_check.append(hand_raised)

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
    print("hand raise check:",hand_raised_check)
    if True not in hand_raised_check:
        print("Not hand raise")
        if malpractice>=5:
            print("saving data..")
            now = datetime.now()
            date_str = now.date().isoformat()       # e.g., '2025-03-24'
            time_str = now.time().strftime('%H:%M:%S')  # e.g., '14:53:12'

            # Update your destination path using full datetime
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            destination_path = f"../media/output_{timestamp}.mp4"
            shutil.copy("output.mp4", destination_path)

            # Make sure your database table has 'date' and 'time' fields
            sql = "INSERT INTO app_malpraticedetection (date, time, malpractice, proof) VALUES (%s, %s, %s, %s)"
            values = (date_str, time_str, "Hand Raised", f"output_{timestamp}.mp4")
            cursor.execute(sql, values)
            db.commit()

            db.commit()
            print("Data inserted successfully")
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
