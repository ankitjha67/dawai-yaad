# Dawai Yaad — Complete Project Plan
## Open-Source Family Health Platform

> **10 Sessions. Fully Open Source. Built for India.**

---

## Why NOT Supabase → PostgreSQL + FastAPI

Supabase managed service has restricted/unreliable access from India. After evaluating all alternatives:

- **Supabase (managed):** India access issues, vendor lock-in
- **Appwrite:** Good Flutter SDK, but document-DB not ideal for complex relational healthcare data
- **PocketBase:** SQLite-based, not built for multi-tenant hospital scale
- **Nhost:** GraphQL-first adds unnecessary complexity

**CHOSEN: PostgreSQL + FastAPI + SQLAlchemy** — Full control, zero vendor dependency, production-grade for healthcare, works on any Indian VPS.

---

## 100% Open Source Tech Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Backend API | FastAPI (Python) | MIT |
| ORM | SQLAlchemy + Alembic | MIT |
| Database | PostgreSQL 16 | PostgreSQL License |
| Cache/Queue | Redis | BSD |
| Task Scheduler | Celery | BSD |
| Push Notifications | Firebase Cloud Messaging | Free |
| File Storage | MinIO (S3-compatible) | AGPL |
| Mobile App | Flutter 3.x | BSD |
| Web Dashboard | Next.js 14 | MIT |
| Auth | JWT + Phone OTP (MSG91) | — |
| Real-time | FastAPI WebSockets | MIT |
| PDF Reports | WeasyPrint | BSD |
| Containerization | Docker Compose | Apache 2.0 |

---

## 10 Session Build Plan

| # | Session | Deliverable |
|---|---------|------------|
| 1 | **Backend Foundation** | FastAPI scaffold, PostgreSQL models, Auth (JWT+OTP), Medication CRUD, Docker Compose |
| 2 | **Family & Caregivers** | Family CRUD, relationship mapping, RBAC middleware, caregiver endpoints, permission checks |
| 3 | **Reminder Engine** | Celery setup, daily/hourly task generation, escalation chain, FCM push integration |
| 4 | **SOS & Real-time** | WebSocket SOS, trigger/confirm/acknowledge/resolve flow, critical push alerts |
| 5 | **Hospital/Nurse** | Hospital registration, nurse assignment, dose logging by nurse, ward dashboard data |
| 6 | **Documents & Reports** | MinIO file storage, blood report upload, PDF report generation, WhatsApp sharing |
| 7 | **Flutter App — Core** | Auth screens, home schedule, mark dose taken, family profile switcher |
| 8 | **Flutter App — Full** | Caregiver mode, SOS button, measurements, documents, settings |
| 9 | **Flutter App — Notifications** | FCM integration, local alarms, background service, SOS alarm sound |
| 10 | **Next.js Dashboard** | Nurse dashboard, caregiver dashboard, real-time SOS, PDF download |

---

## RBAC (Role-Based Access Control)

| Role | Can Do |
|------|--------|
| **Patient** | View own meds, mark taken, log vitals, trigger SOS, view own reports |
| **Family Caregiver** | All patient actions + add/edit/delete meds for linked patients, receive SOS, view reports |
| **Nurse** | Manage assigned patients' meds, log administered doses, upload blood reports, generate ward reports |
| **Doctor** | View all patients' reports, medication history, measurement trends, approve/modify prescriptions |
| **Admin** | Full system access, manage users, hospital settings |

---

## Family System

Supports adding unlimited family members with Indian-context relationships:
- Father (Papa), Mother (Mummy)
- Grandfather (Dada/Nana), Grandmother (Dadi/Nani)
- Maternal Uncle (Mama), Paternal Uncle (Chacha/Tau)
- Aunt (Mausi/Chachi/Bua/Mami)
- Any custom relationship

Each member gets: `can_edit` (modify meds), `receives_sos` (get emergency alerts), `receives_missed_alerts` (get missed dose notifications)

---

## SOS Emergency Flow

```
Patient taps SOS → "Are you sure?" confirmation
    ↓ Confirmed
Backend creates alert → FCM CRITICAL push to ALL caregivers
    + WebSocket real-time broadcast
    + If hospitalized → Alert assigned nurse
    + SMS to emergency contacts
    ↓ Caregiver acknowledges
Patient notified "Help is coming from [Name]"
    ↓ Resolved
Logged with timestamp + resolution notes
```

---

## Reminder Escalation Chain

```
T+0 min  → Push notification to patient
T+5 min  → Second push (CRITICAL — bypasses silent mode)
T+15 min → Alert ALL caregivers via push
T+30 min → WhatsApp to patient + caregivers
T+60 min → Mark MISSED, full family alert, nurse if hospitalized
```

---

## Hospital Nurse Features

- Register hospital with departments/wards
- Assign nurses to patients (ward + bed number)
- Nurse dashboard: all assigned patients' medication schedules
- One-tap dose administered logging (with nurse ID)
- Upload blood reports, X-rays, discharge summaries per patient
- Generate ward-level adherence reports as downloadable PDF
- Share reports with doctors via the system

---

## Indian Deployment (self-hosted)

| Provider | Region | Cost |
|----------|--------|------|
| Hetzner Cloud | Finland/India | ~₹800/mo |
| DigitalOcean | Bangalore | ~₹1,200/mo |
| AWS Mumbai | ap-south-1 | ~₹1,500/mo |

Docker Compose = provider-agnostic. Start anywhere, migrate anytime.
