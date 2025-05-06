# 🎓 DetectSus: Real-Time Malpractice Detection in Classrooms Using Computer Vision

> A comprehensive AI-driven system that detects and flags suspicious activities during classroom examinations, leveraging cutting-edge computer vision and deep learning models for enhanced academic integrity.

---

# Live Demonstration
> Click the thumbnail to watch the youtube video

[![DetectSus Demo](https://img.youtube.com/vi/wUmAu1ub52Y/0.jpg)](https://youtu.be/wUmAu1ub52Y)

---

## 🧠 Overview
DetectSus is a real-time surveillance system designed to detect and report instances of malpractice during offline classroom examinations. By combining **object detection** (e.g., detecting prohibited items like mobile phones) and **pose estimation** (e.g., identifying suspicious behaviors like turning around or passing notes), this project aims to provide educational institutions with an **automated, scalable, and privacy-focused** exam monitoring solution.

❓**Why DetectSus?**
- Traditional invigilation struggles to catch subtle, tech-enabled cheating in large classrooms.
- Modern **deep learning** techniques offer faster, more reliable detection.
- **Offline-first design** ensures local data processing and privacy, avoiding cloud dependencies.
- Easily adoptable in educational settings with minimal extra hardware.

---

## 🚀 Key Features
- **Real-Time Detection:** Operates at high frame rates, identifying suspicious actions (e.g., looking sideways, leaning, passing notes) and objects (e.g., cell phones).
- **Pose Estimation:** Uses YOLOv8-based pose models to track skeletal keypoints of students, flagging suspicious postures.
- **Secure & Offline:** Runs locally on standard hardware (laptop/desktop + webcam). No internet connection required.
- **Automated Evidence Collection:** Crops and saves short video clips of suspicious events, embedding metadata (date, time, classroom).
- **Admin Dashboard:** A Django-based interface for real-time alerts, manual review of flagged events, and logging.
- **Scalable & Modular:** Supports multiple cameras (front, corner, or top views). Easily extended or integrated into existing environments.

---

## ⛏️ Project Architecture
A high-level flow of how DetectSus operates in the classroom:

1. **Video Capture:**
   - One or more webcams capture live footage from strategic angles (front/top corner).
   - Each camera feed is handled by a separate script or thread.

2. **Object Detection & Pose Estimation:**
   - **YOLOv8** (object detection) locates entities like *students, teachers, phones, or notes*.
   - **YOLOv8-Pose** (pose estimation) identifies keypoints (e.g., shoulders, wrists, eyes) to determine suspicious gestures (turning back, leaning, passing).
   - Models run in real-time and output bounding boxes & keypoints.

3. **Suspicious Activity Check:**
   - The system checks if a threshold of frames confirms unauthorized devices or gestures.
   - If confirmed, triggers “proof recording” to capture a short video snippet.

4. **Proof Generation & Transfer:**
   - The snippet is saved locally and optionally **SCP**-transferred to a central server.
   - Metadata (exam hall, time, type of malpractice) is recorded in a MySQL database.

5. **Admin Dashboard & Review:**
   - A Django web interface displays alerts and embedded videos.
   - Authorized staff can mark each event as “Malpractice” or “Not Malpractice.”
   - Notifications (email/SMS) can be sent to invigilators assigned to that classroom.

---

## ⚙️ Installation & Setup
Follow these steps to get the DetectSus system up and running.

### 1. Prerequisites
- **Operating System:** Windows 10/11, or Ubuntu 20.04+ recommended.
- **Hardware:** 
  - Webcam (1080p recommended).
  - CPU with at least 4 cores (Intel i5/i7 or equivalent).
  - **Optional:** GPU (NVIDIA RTX series) for higher FPS but not mandatory.
- **Software Packages:**
  - Python 3.10+ 
  - MySQL or MariaDB (for storing detection logs).
  - Git (if you plan to clone the repository).
  - [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) installed via `pip`.

### 2. Repository Cloning
```bash
git clone https://github.com/noelmathen/DetectSus---Real-Time-Malpractice-Detection-System-in-Classrooms-using-Computer-Vision.git
cd DetectSus---Real-Time-Malpractice-Detection-System-in-Classrooms-using-Computer-Vision
```

### 3. Python Environment
Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate      # Linux or Mac
.\venv\Scripts\activate       # Windows
```

### 4. Install Requirements
```bash
pip install -r requirements.txt
```
(This installs **Django**, **OpenCV**, **Ultralytics YOLOv8**, **paramiko**, **scp**, and other dependencies.)

### 5. Database Configuration
1. Install and configure MySQL on your system.
2. Update database credentials in `app/settings.py` or environment variables (`.env`).
3. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### 6. Run the Django Server
```bash
python manage.py runserver
```
- Access the web interface at `http://127.0.0.1:8000/`.

### 7. Configure & Run Camera Scripts
- Edit the relevant Python scripts in `ML/` (e.g., `front.py`, `top_corner.py`) to:
  - Set `IS_CLIENT = False` if running on the same machine as server, or `True` if on a separate client PC.
  - Adjust lecture hall info, building name, camera index, etc.
- Launch the desired script:
  ```bash
  python ML/front.py
  ```
- Confirm the camera feed opens and logs appear in the console.  

---

## 👨‍🏫 Usage
1. **Start Django Admin Dashboard**  
   `python manage.py runserver`

2. **Open Browser & Login**  
   - Navigate to `http://localhost:8000/login`.
   - Use Admin credentials or create a Teacher profile.

3. **Run Camera Scripts**  
   - On the same or separate computer, run `python ML/front.py` or `python ML/top_corner.py` to begin capturing exam footage.

4. **Review Alerts**  
   - In real-time, any suspicious actions (leaning, turning, phone usage, passing) trigger short proof recordings.
   - Admin or assigned teacher visits **Malpractice Log** page to see new alerts, watch the snippet, and verify or reject.

5. **Notifications (Optional)**  
   - If configured, the system sends email or SMS whenever an admin confirms an event as malpractice.

---

## 🗂️ Project Structure

```
DetectSus/
├── app/
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0003_auto_20250311_1410.py
│   │   ├── 0014_alter_lecturehall_building.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── asgi.py
│   ├── custom_email_backen.py
│   ├── forms.py
│   ├── models.py
│   ├── settings.py
│   ├── urls.py
│   ├── utils.py
│   ├── views.py
│   └── wsgi.py
├── ML/
│   ├── front.py
│   ├── hand_raise.py
│   ├── leaning.py
│   ├── mobile_detection.py
│   ├── passing_paper.py
│   ├── top_corner.py
│   ├── top.py
│   ├── turning_back.py
│   ├── asgi.py
│   ├── yolov8n.pt
│   ├── yolov8n-pose.pt
│   └── test_videos/
├── media/
│   ├── profile_pics/
│   ├── output_passingpaper_2025-04-10_11-03-14.mp4
│   ├── output_mobiledetection_2025-04-10_10-15-59.mp4
│   ├── output_turningback_2025-04-09_22-44-03.mp4
├── static/
│   ├── img/
│   │   ├── about_detectsus.png
│   │   ├── banner.jpg
│   │   ├── icon.svg
│   │   └── background.png
├── templates/
│   ├── change_password.html
│   ├── edit_profile.html
│   ├── header.html
│   ├── footer.html
│   ├── index.html
│   ├── login.html
│   ├── malpractice_log.html
│   ├── manage_lecture_halls.html
│   ├── profile.html
│   ├── run_cameras.html
│   ├── teacher_register.html
│   ├── view_teachers.html
├── README.md
├── manage.py
├── .env         
├── .gitignore
├── requirements.txt
```


---

## 🧠 ML Models Used

- `yolov8n.pt` — Object Detection (e.g., phones)
- `yolov8n-pose.pt` — Pose Estimation
- Custom Python scripts for each type of malpractice behavior


---

## 👨‍💻 Team Contributors

- Allen Prince
- Dea Elizabeth Varghese
- Noel Mathen Eldho
- Shruti Maria Shibu

---


## 📑 Research Papers & Reports
1. **_[Object Detection for Real-Time Malpractice Detection in Classrooms Using Computer Vision](https://doi.org/10.52783/jisem.v10i33s.5464)_**  
   [Journal of Information Systems Engineering and Management (2025)]  
   Explores YOLOv8-based object detection approaches tuned for exam settings.

2. **_[DetectSus: Real-Time Malpractice Detection in Classrooms using Computer Vision](https://drive.google.com/file/d/1qLmjFetZ2R0SZIOs1A6W8YhnkpZz9DrS/view?usp=sharing)_**  
   Final B.Tech project **Phase 1** report covering methodology, system design, dataset usage, UML diagrams, basic flow and so on.

3. **_[DetectSus: Real-Time Malpractice Detection in Classrooms using Computer Vision](https://drive.google.com/file/d/1HOTdLsKUV04Cmku7_PU-uK-k0Kxv7aIW/view?usp=sharing)_**  
   Final B.Tech project **Phase 2** report covering methodology, pilot deployment results, code working, output screenshots and so on.
   
   
These papers and reports detail the **theoretical underpinnings** and **benchmark evaluations** guiding DetectSus.

---

## 🛂 Contributing
We welcome contributions! Please:
1. **Fork** the repository on GitHub.
2. Create a **feature branch** (`git checkout -b feature/NewModule`).
3. Make changes, **commit**, and push to your branch.
4. Submit a **pull request** describing improvements or bug fixes.

---
