#turning_back.py
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
    video_path = "test_videos/Top_Corner.mp4"
    cap = cv2.VideoCapture(video_path)


# Set resolution
frame_width, frame_height = 1280, 720


def is_turning_back(keypoints):
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
    if eye_dist < 0.4 * shoulder_dist and left_ear[0] > left_eye[0] and right_ear[0] < right_eye[0]:
        return True

    return False

malpractice = 0
video_control = 0


while cap.isOpened():
    turning_back_check = list()
    turning_back = False
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


            if is_turning_back(kp):
                print("Checking turning back")
                malpractice = malpractice + 1
                cv2.putText(frame, "Turning back!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
                turning_back = True

                

            # Draw keypoints (default color green)
            if not turning_back:
                for x, y in kp[:6]:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
            for x, y in kp[6:]:
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

            turning_back_check.append(turning_back)

    
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
    print("Turning back check:",turning_back_check)
    if True not in turning_back_check:
        print("Not turning back")
        if malpractice>=10:
            print("saving data..")
            now = datetime.now()
            date_str = now.date().isoformat()       # e.g., '2025-03-24'
            time_str = now.time().strftime('%H:%M:%S')  # e.g., '14:53:12'

            lecture_hall_name = "LH2"
            building = "KE Block"

            # Fetch the lecture hall object
            cursor.execute(
                "SELECT id FROM app_lecturehall WHERE hall_name = %s AND building = %s LIMIT 1",
                (lecture_hall_name, building)
            )
            hall_result = cursor.fetchone()
            hall_id = hall_result[0] if hall_result else None

            # Save the output video
            timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
            proof_filename = f"output_{timestamp}.mp4"
            destination_path = f"../media/{proof_filename}"
            shutil.copy("output.mp4", destination_path)

            # Insert into malpractice table
            sql = """
                INSERT INTO app_malpraticedetection (date, time, malpractice, proof, lecture_hall_id)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (date_str, time_str, "Turning Back", proof_filename, hall_id)
            cursor.execute(sql, values)
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
