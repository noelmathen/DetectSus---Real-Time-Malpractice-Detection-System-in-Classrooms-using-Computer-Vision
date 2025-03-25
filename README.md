# 🎓 DetectSus - Real-Time Malpractice Detection System

DetectSus is a real-time classroom monitoring system developed using **Django**, **MySQL**, and **Computer Vision** techniques. It detects malpractice behaviors such as mobile usage, turning back, passing papers, and hand-raising using **YOLOv8** and **pose estimation**, and logs them securely with timestamped video proof.

---

## 🚀 Features

- 🎥 Real-time camera monitoring
- 🧠 Malpractice detection using YOLOv8, pose models, and custom logic
- 📂 Logs suspicious activity with timestamped video proof
- 👨‍🏫 Admin and Teacher login support
- 🔐 Django authentication system
- 📊 Web interface for log review and verification
- 📨 Email notification setup (with `.env` support)
- 🌐 Responsive and modern UI

---

## 🗂️ Project Structure

```
application/
├── app/
│   ├── migrations/
│   ├── __init__.py
│   ├── asgi.py
│   ├── models.py
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   └── wsgi.py
│
├── ML/
│   ├── hand_raise.py
│   ├── leaning.py
│   ├── mobile_detection.py
│   ├── passing_paper.py
│   ├── turning_back.py
│   ├── test_videos/
│   └── yolov8n.pt, yolov8n-pose.pt, yolo11m.pt
│
├── media/                     # Stores video proofs
├── static/                    # CSS, JS, Images
├── templates/                 # HTML Templates
│   ├── header.html
│   ├── footer.html
│   ├── login.html
│   ├── register.html
│   ├── index.html
│   └── malpractice_log.html
├── manage.py
└── .env                       # Hidden file for environment secrets
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/DetectSus.git
cd DetectSus
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure `.env` File

Create a `.env` file in the root and add:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=detectsus@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
```

### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run the Server

```bash
python manage.py runserver
```

---

## 📸 How It Works

- The admin/teacher logs in to the system.
- Real-time camera feed is processed by YOLO and pose estimation models.
- Detected malpractices are stored in the database with video proof.
- Admin reviews logs and approves/rejects malpractice claims.
- Approved logs are visible to teachers on their dashboard.

---

## 🧠 ML Models Used

- `yolov8n.pt` — Object Detection (e.g., phones)
- `yolov8n-pose.pt` — Pose Estimation
- Custom Python scripts for each type of malpractice behavior

---

## 🛡️ Security

- Passwords are securely hashed using Django auth
- Admin approval workflow for sensitive logs
- Environment variables managed via `.env`

---

## 📄 .gitignore

Make sure the following are ignored:

```
__pycache__/
*.pyc
*.pyo
*.pyd
*.sqlite3
*.log
media/
venv/
.env
*.pt
.DS_Store
```

---

## 👨‍💻 Team Contributors

- Allen Prince
- Dea Elizabeth Varghese
- Noel Mathen Eldho
- Shruti Maria Shibu

---

## 🏁 Future Enhancements

- Email alerts to admins/teachers
- Student facial recognition
- Enhanced multi-user role management
- Live dashboard with charts/analytics

---
