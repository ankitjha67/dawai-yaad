# Dawai Yaad — Claude Code Windows Setup Guide
## Complete Step-by-Step: From Download to All 10 Sessions

---

## PHASE 1: Prerequisites (One-Time Setup)

### Step 1: Install Docker Desktop for Windows

Docker runs PostgreSQL, Redis, MinIO — everything the backend needs.

1. Download from: https://www.docker.com/products/docker-desktop/
2. Run the installer
3. **IMPORTANT:** During install, ensure "Use WSL 2 instead of Hyper-V" is checked
4. Restart your PC when prompted
5. Open Docker Desktop and let it finish initializing
6. Verify in PowerShell:

```powershell
docker --version
docker-compose --version
```

### Step 2: Install Python 3.12+

1. Download from: https://www.python.org/downloads/
2. **IMPORTANT:** Check "Add Python to PATH" during install
3. Verify:

```powershell
python --version
pip --version
```

### Step 3: Install Node.js 20+ (for Next.js dashboard later)

1. Download LTS from: https://nodejs.org/
2. Install with defaults
3. Verify:

```powershell
node --version
npm --version
```

### Step 4: Install Flutter (for mobile app later)

1. Download from: https://docs.flutter.dev/get-started/install/windows/mobile
2. Extract to `C:\flutter`
3. Add `C:\flutter\bin` to your PATH:
   - Search "Environment Variables" in Start Menu
   - Edit PATH → Add `C:\flutter\bin`
4. Open new PowerShell and verify:

```powershell
flutter doctor
```

5. Install Android Studio from: https://developer.android.com/studio
6. In Android Studio → Settings → SDK Manager → Install Android SDK
7. Run `flutter doctor` again — fix any remaining issues it flags

### Step 5: Install Git

1. Download from: https://git-scm.com/download/win
2. Install with defaults
3. Configure:

```powershell
git config --global user.name "Ankit Jha"
git config --global user.email "your-email@example.com"
```

### Step 6: Install PostgreSQL client tools (optional but helpful)

```powershell
# Or just use Docker for everything — this is optional
# pgAdmin is a good GUI: https://www.pgadmin.org/download/
```

---

## PHASE 2: Project Setup

### Step 7: Download and Extract the Project

1. Download `dawai-yaad-session1-backend.zip` from this chat
2. Extract to your working directory:

```powershell
# Create project directory
mkdir E:\Python\dawai-yaad
# Extract zip contents into E:\Python\dawai-yaad
# You should see: E:\Python\dawai-yaad\dawai-yaad\
# Move contents up one level so structure is:
# E:\Python\dawai-yaad\backend\
# E:\Python\dawai-yaad\docker-compose.yml
# E:\Python\dawai-yaad\README.md
# etc.
```

Or using PowerShell:

```powershell
cd E:\Python
Expand-Archive -Path "$HOME\Downloads\dawai-yaad-session1-backend.zip" -DestinationPath .
# If nested, move up:
Move-Item E:\Python\dawai-yaad\dawai-yaad\* E:\Python\dawai-yaad\ -Force
```

### Step 8: Initialize Git Repository

```powershell
cd E:\Python\dawai-yaad
git init
git add .
git commit -m "Session 1: Backend foundation - FastAPI + PostgreSQL + Auth + Medications API"
```

### Step 9: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `dawai-yaad`
3. Description: "Open-source family health platform — medication reminders, SOS alerts, hospital integration"
4. Set to **Public** (it's open source!)
5. Do NOT initialize with README (we already have one)
6. Push:

```powershell
cd E:\Python\dawai-yaad
git remote add origin https://github.com/ankitjha67/dawai-yaad.git
git branch -M main
git push -u origin main
```

### Step 10: Setup Environment File

```powershell
cd E:\Python\dawai-yaad
copy .env.example .env
```

Edit `.env` with notepad or VS Code — for development, defaults work fine.

### Step 11: Start Docker Services

```powershell
cd E:\Python\dawai-yaad
docker-compose up -d
```

Wait 30-60 seconds for all services to start. Verify:

```powershell
docker-compose ps
```

You should see 6 containers running: dawai_db, dawai_redis, dawai_minio, dawai_api, dawai_celery, dawai_beat

### Step 12: Verify Everything Works

```powershell
# Check API is running
curl http://localhost:8000/

# Open Swagger docs in browser
start http://localhost:8000/docs

# Open MinIO console
start http://localhost:9001
# Login: dawai_minio / dawai_minio_secret
```

---

## PHASE 3: Using Claude Code for Sessions 2-10

### Step 13: Open Claude Code

1. Open the **Claude Code** Windows app
2. Navigate to your project:

```
cd E:\Python\dawai-yaad
```

Or if Claude Code opens with a directory picker, select `E:\Python\dawai-yaad`

### Step 14: Give Claude Code the Context

Paste this as your FIRST message to Claude Code:

```
Read the entire project structure. This is an open-source family health 
platform called "Dawai Yaad" (Medicine Reminder). Session 1 (backend 
foundation) is complete with:

- FastAPI backend with SQLAlchemy async ORM
- 10 PostgreSQL models (User, Family, Medication, DoseLog, Measurement, 
  MoodLog, SymptomLog, SOSAlert, Document, Hospital/Staff/Assignment, 
  Notification)
- Auth system (Phone OTP + JWT + RBAC)
- Medication CRUD API with dose logging
- Health tracking API (BP, sugar, weight, mood, symptoms)
- SOS emergency API with WebSocket
- Celery task stubs for reminders
- Docker Compose (PostgreSQL + Redis + MinIO + FastAPI + Celery)
- 22 pytest tests

The project has 10 sessions total. I need you to build Sessions 2-10 
one at a time. Start with Session 2.

Read README.md for full context, then read all files in backend/app/ 
to understand the patterns.
```

### Step 15: Build Session 2 — Family & Caregivers

Tell Claude Code:

```
Build Session 2: Family & Caregiver System

1. Create backend/app/api/families.py with these endpoints:
   - POST /families — Create a family ("Jha Family")
   - GET /families — List user's families
   - GET /families/{id}/members — List members with user details
   - POST /families/{id}/members — Add member by phone number 
     (with relationship like father, mother, grandmother_maternal, etc.)
   - PUT /families/{id}/members/{mid} — Update permissions 
     (can_edit, receives_sos, receives_missed_alerts)
   - DELETE /families/{id}/members/{mid} — Remove member

2. Create backend/app/api/caregivers.py with these endpoints:
   - GET /caregiver/patients — List patients I'm caregiver for
   - POST /caregiver/{patient_id}/medications — Add med for my patient
   - PUT /caregiver/{patient_id}/medications/{id} — Edit their med
   - POST /caregiver/{patient_id}/medications/{id}/taken — Log dose for them

3. Create RBAC middleware in backend/app/utils/permissions.py:
   - check_family_permission(user, patient_id) — verify caregiver relationship
   - check_can_edit(user, patient_id) — verify can_edit flag is true
   - Apply these checks in caregiver endpoints

4. Add routes to backend/app/api/__init__.py

5. Write tests in backend/tests/test_families.py

6. Run tests: pytest tests/ -v

7. Git commit: "Session 2: Family & caregiver system with RBAC"
```

### Step 16: Build Session 3 — Reminder Engine

```
Build Session 3: Reminder Engine with Celery + FCM

1. Implement backend/app/tasks/reminders.py:
   - generate_daily_reminders(): Query all active medications, 
     check which are due today using the _is_due_on logic from 
     medications.py, schedule individual send_reminder tasks
   - For hourly meds: generate tasks at each interval 
     (e.g., every 4 hrs from 8 AM to 10 PM = tasks at 8,12,16,20)
   - send_reminder(user_id, medication_id, escalation_level):
     Level 0 (T+0): Send FCM push to patient
     Level 1 (T+5min): Send critical FCM push
     Level 2 (T+15min): Push to all caregivers
     Level 3 (T+30min): Mark as missed
   - check_missed_doses(): Find doses past due time without log, 
     create missed DoseLog entries, alert caregivers
   - send_stock_alerts(): Find low stock meds, push to user

2. Implement backend/app/services/fcm.py:
   - Initialize firebase_admin SDK
   - send_push(fcm_token, title, body, data, priority)
   - send_critical_push() — for SOS and escalated reminders

3. Update Celery beat schedule in tasks/__init__.py

4. Test with: celery -A app.tasks worker --loglevel=debug

5. Git commit: "Session 3: Celery reminder engine with escalation"
```

### Step 17: Build Session 4 — SOS Real-time

```
Build Session 4: SOS Real-time System

1. Enhance backend/app/api/sos.py:
   - Use Redis pub/sub instead of in-memory dict for WebSocket 
     connections (so it works across multiple workers)
   - When SOS triggered: query all family_members where 
     receives_sos=True, send FCM critical push to each
   - When SOS triggered + patient is hospitalized: also alert 
     assigned nurse via patient_assignments table
   - Add GET /sos/history — past resolved SOS alerts

2. Create backend/app/services/websocket_manager.py:
   - Redis-backed WebSocket connection manager
   - Broadcast to family group
   - Heartbeat/ping-pong

3. Write tests for SOS + family alert flow

4. Git commit: "Session 4: Real-time SOS with Redis pub/sub"
```

### Step 18: Build Session 5 — Hospital/Nurse

```
Build Session 5: Hospital & Nurse Integration

1. Create backend/app/api/hospitals.py:
   - POST /hospitals — Register hospital
   - POST /hospitals/{id}/staff — Add nurse/doctor to hospital
   - GET /hospitals/{id}/staff — List staff
   
2. Create backend/app/api/nurse.py:
   - GET /nurse/patients — List my assigned patients
   - GET /nurse/patients/{pid}/schedule — Patient's today schedule
   - POST /nurse/patients/{pid}/dose-log — Log dose I administered
   - POST /nurse/patients/{pid}/documents — Upload blood report
   - GET /nurse/ward-report — Adherence report for all my patients

3. Patient assignment endpoints:
   - POST /hospitals/{id}/assign — Assign nurse to patient
   - PUT /hospitals/{id}/assign/{id} — Update ward/bed
   - POST /hospitals/{id}/discharge/{pid} — Discharge patient

4. Apply role-based checks: only nurse/doctor roles can access

5. Tests + git commit: "Session 5: Hospital nurse integration"
```

### Step 19: Build Session 6 — Documents & Reports

```
Build Session 6: Documents & PDF Reports

1. Create backend/app/services/storage.py:
   - MinIO client initialization
   - upload_file(file, bucket, path) → URL
   - download_file(path) → bytes
   - delete_file(path)

2. Create backend/app/api/documents.py:
   - POST /documents/upload — Upload blood report/prescription 
     (multipart form, store in MinIO)
   - GET /documents — List user's documents
   - GET /documents/{id}/download — Download file
   - DELETE /documents/{id}

3. Create backend/app/services/report_generator.py:
   - generate_adherence_report(user_id, days) → PDF bytes
   - Uses WeasyPrint to create styled HTML → PDF
   - Includes: patient info, medication list with doses/units, 
     7-day adherence bar chart, measurement history, mood trend,
     recent symptoms, doctor visit notes

4. Create backend/app/api/reports.py:
   - GET /reports/adherence — JSON adherence data
   - GET /reports/pdf — Download PDF report
   - POST /reports/share — Share via email (stub for WhatsApp)

5. Tests + git commit: "Session 6: MinIO documents + PDF reports"
```

### Step 20: Build Session 7 — Flutter App Core

```
Build Session 7: Flutter App — Foundation

1. Create Flutter project:
   cd E:\Python\dawai-yaad
   flutter create mobile --org com.dawaiyaad
   cd mobile

2. Add dependencies to pubspec.yaml:
   - dio (HTTP client)
   - flutter_riverpod (state management)
   - go_router (navigation)
   - flutter_secure_storage (JWT storage)
   - shared_preferences
   - intl (date formatting)

3. Create project structure:
   lib/
   ├── main.dart
   ├── config/
   │   ├── api_client.dart (Dio + JWT interceptor)
   │   ├── routes.dart
   │   └── theme.dart (green medical theme)
   ├── models/ (Dart classes matching Pydantic schemas)
   ├── providers/ (Riverpod providers)
   ├── screens/
   │   ├── auth/
   │   │   ├── phone_screen.dart
   │   │   └── otp_screen.dart
   │   ├── home/
   │   │   ├── home_screen.dart (today's schedule)
   │   │   └── medication_card.dart
   │   ├── add_medication/
   │   │   └── add_medication_screen.dart
   │   └── profile/
   │       └── profile_screen.dart
   └── widgets/ (shared components)

4. Implement auth flow:
   - Phone number input → send OTP → verify → store JWT
   - Auto-refresh on 401
   
5. Implement home screen:
   - Fetch today's schedule from API
   - Group by meal slot
   - One-tap mark as taken
   - Pull to refresh

6. Test on Android emulator or connected device

7. Git commit: "Session 7: Flutter app core — auth + home + dose logging"
```

### Step 21: Build Session 8 — Flutter Full Features

```
Build Session 8: Flutter App — All Features

1. Family management screens:
   - Family list → member list → add member (phone + relationship)
   - Profile switcher in app bar (Papa/Mummy/Dadi...)

2. Caregiver mode:
   - When viewing a linked patient's profile, show their schedule
   - Add/edit medications for them
   - Mark doses on their behalf

3. SOS button:
   - Big red button on home screen
   - Confirmation dialog with 3-second countdown
   - Triggers API call + shows "Help requested" state
   - Plays alarm sound when receiving SOS from family member

4. Health tracking screens:
   - Measurements (BP, sugar, weight with input + history chart)
   - Mood picker
   - Symptom multi-select

5. Document screens:
   - Upload prescription photo from camera/gallery
   - View uploaded documents list
   - Download/share documents

6. Settings screen:
   - Privacy mode toggle
   - Language preference
   - Notification preferences
   - Family management

7. Git commit: "Session 8: Flutter full features — family, SOS, health, docs"
```

### Step 22: Build Session 9 — Flutter Notifications

```
Build Session 9: Flutter Push Notifications + Background Alarms

1. Setup Firebase:
   - Create Firebase project at console.firebase.google.com
   - Add Android app (package: com.dawaiyaad.mobile)
   - Download google-services.json → mobile/android/app/
   - Add Firebase dependencies to build.gradle

2. Add packages:
   - firebase_core
   - firebase_messaging
   - flutter_local_notifications
   - android_alarm_manager_plus
   - workmanager (background tasks)
   - audioplayers (for SOS alarm sound)

3. Implement FCM handling:
   - Foreground: show local notification with medication name
   - Background: handle in background isolate
   - Tap: navigate to medication detail
   - Critical alerts: bypass DND for SOS

4. Local backup alarms:
   - Schedule local notifications matching medication times
   - Use android_alarm_manager for reliability when app is killed
   - Workmanager for periodic sync

5. SOS alarm:
   - When receiving SOS push, play loud alarm sound
   - Show full-screen alert even when app is closed
   - Vibrate continuously until acknowledged

6. Test on physical Android device (emulator lacks push)

7. Git commit: "Session 9: FCM push + local alarms + SOS alarm sound"
```

### Step 23: Build Session 10 — Next.js Dashboard

```
Build Session 10: Next.js Web Dashboard

1. Create Next.js project:
   cd E:\Python\dawai-yaad
   npx create-next-app@latest web --typescript --tailwind --app
   cd web

2. Install dependencies:
   - axios (API client)
   - @tanstack/react-query (data fetching)
   - recharts (charts)
   - lucide-react (icons)
   - date-fns

3. Build pages:
   src/app/
   ├── page.tsx (landing page)
   ├── login/page.tsx (phone OTP login)
   ├── dashboard/
   │   ├── page.tsx (patient home — today's schedule)
   │   ├── family/page.tsx (family member management)
   │   ├── reports/page.tsx (adherence reports + PDF download)
   │   └── documents/page.tsx (view uploaded documents)
   ├── caregiver/
   │   ├── page.tsx (list patients I manage)
   │   └── [patientId]/page.tsx (manage patient's meds)
   └── nurse/
       ├── page.tsx (my assigned patients)
       ├── [patientId]/page.tsx (patient schedule + dose logging)
       └── ward-report/page.tsx (ward-level adherence PDF)

4. Real-time SOS display:
   - WebSocket connection to /api/v1/sos/ws/{userId}
   - Full-screen red alert when SOS received
   - Acknowledge button sends API call

5. Deploy to Vercel:
   - Connect GitHub repo
   - Set environment variable: NEXT_PUBLIC_API_URL=https://your-vps-ip:8000
   - Deploy

6. Git commit: "Session 10: Next.js dashboard — nurse + caregiver + SOS"
```

---

## PHASE 4: Deployment

### Step 24: Deploy Backend to DigitalOcean Bangalore

```
After all sessions are complete, deploy:

1. Create DigitalOcean account: https://www.digitalocean.com/
2. Create Droplet:
   - Region: Bangalore (BLR1)
   - Image: Ubuntu 24.04
   - Size: Basic, 4GB RAM ($24/mo ≈ ₹2,000/mo)
   - Add your SSH key

3. SSH into droplet:
   ssh root@your-droplet-ip

4. Install Docker:
   curl -fsSL https://get.docker.com | sh
   apt install docker-compose-plugin

5. Clone your repo:
   git clone https://github.com/ankitjha67/dawai-yaad.git
   cd dawai-yaad

6. Setup environment:
   cp .env.example .env
   nano .env  # Set production secrets

7. Start everything:
   docker compose up -d

8. Setup domain (optional):
   - Buy domain from Namecheap/GoDaddy
   - Point A record to droplet IP
   - Install Caddy for auto-HTTPS:
     apt install caddy
     # Caddyfile: api.dawaiyaad.in → localhost:8000
```

### Step 25: Deploy Web Dashboard to Vercel

```
1. Go to https://vercel.com/
2. Import GitHub repo: ankitjha67/dawai-yaad
3. Set root directory: web/
4. Set environment variable:
   NEXT_PUBLIC_API_URL=https://api.dawaiyaad.in
5. Deploy — Vercel gives you free .vercel.app URL
```

---

## Quick Reference: Claude Code Session Commands

Copy-paste these into Claude Code one session at a time:

```
# Before each session, make sure Docker is running:
docker-compose ps

# After each session:
pytest tests/ -v
git add .
git commit -m "Session N: description"
git push origin main
```

---

## Troubleshooting

### Docker won't start on Windows
- Open Docker Desktop → Settings → General → "Use WSL 2 based engine"
- Restart Docker Desktop
- If still failing: Windows Features → enable "Virtual Machine Platform" + "WSL"

### Port 5432 already in use
- You might have a local PostgreSQL running
- Stop it: `net stop postgresql-x64-16` (or whatever version)
- Or change port in docker-compose.yml: `"5433:5432"`

### Flutter doctor shows issues
- Run `flutter doctor --verbose` for details
- Most common: accept Android licenses: `flutter doctor --android-licenses`

### Tests fail with "cannot connect to database"
- Make sure Docker containers are running: `docker-compose ps`
- Tests use SQLite, not PostgreSQL, so Docker isn't needed for tests
- But you need: `pip install aiosqlite`

### Claude Code can't find project files
- Make sure you've cd'd into the project: `cd E:\Python\dawai-yaad`
- Verify: `ls` or `dir` should show backend/, docker-compose.yml, etc.
