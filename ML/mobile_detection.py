#mobile_detection.py
from ultralytics import YOLO
import cv2
import numpy as np
from datetime import datetime
import mysql.connector
import shutil
import os

# MySQL Connection (Ensure consistency)
db = mysql.connector.connect(
    host="localhost",     
    user="root",          
    password="", 
    database="exam_monitoring"
)
cursor = db.cursor()

# Load YOLOv8 model for mobile detection
model = YOLO("yolo11m.pt")  # Use a trained model if available

# Choose between webcam or video file
use_camera = True  

if use_camera:
    cap = cv2.VideoCapture(1)  # 0 is the default webcam
else:
    video_path = "test_videos/Phone_2.mp4"
    cap = cv2.VideoCapture(video_path)

# Set resolution
frame_width, frame_height = 1280, 720

# Malpractice tracking variables (Same as `leaning.py`)
malpractice = 0
video_control = 0
out = None  # Ensure 'out' is defined

while cap.isOpened():
    mobile_check = []  # Track per-frame detections
    mobile_detected = False

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (frame_width, frame_height))

    # Run YOLO inference
    results = model(frame)

    # Store detected mobile phone bounding boxes
    cell_phone_detections = []

    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                if int(box.cls) == 67:  # Mobile phone class ID
                    x1, y1, x2, y2 = map(int, box.xyxy[0])  # Bounding box coordinates
                    cell_phone_detections.append((x1, y1, x2, y2))
                    mobile_detected = True

    # If a mobile phone is detected
    if mobile_detected:
        malpractice += 1
        cv2.putText(frame, "Mobile Detected!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Draw bounding boxes for mobile detection
        for (x1, y1, x2, y2) in cell_phone_detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)  # Orange color
            cv2.putText(frame, "Mobile", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    # Track detections
    mobile_check.append(mobile_detected)

    # Start video recording if malpractice is detected
    if malpractice >= 1:
        if video_control == 0:
            print("Started video recording..")
            video_control = 1
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter("output.mp4", fourcc, 30, (frame_width, frame_height))

        out.write(frame)  # Save the frame

    print("Mobile detection check:", mobile_check)

    # Stop recording & log malpractice if mobile detection persists
    if True not in mobile_check:
        print("No mobile detected")
        if malpractice >= 3:
            print("Saving malpractice evidence..")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            # Ensure 'out' is released before saving
            if out is not None:
                out.release()

            destination_path = f"../media/malpractice_{timestamp}.mp4"

            # Ensure the directory exists
            destination_folder = os.path.dirname(destination_path)
            os.makedirs(destination_folder, exist_ok=True)

            shutil.copy("output.mp4", destination_path)

            # Insert malpractice event into MySQL (EXACTLY like `leaning.py`)
            sql = "INSERT INTO app_malpraticedetection (time, malpractice, proof) VALUES (%s, %s, %s)"
            values = (timestamp, "Mobile Phone Usage", f"./{destination_path}")
            cursor.execute(sql, values)
            db.commit()

            malpractice = 0
            video_control = 0
        else:
            if video_control == 1:
                if out is not None:
                    out.release()
                malpractice = 0
                video_control = 0

    # Display the frame
    cv2.imshow("Exam Monitoring - Mobile Detection", frame)

    # Break on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release resources
cap.release()
if out is not None:
    out.release()
cv2.destroyAllWindows()
