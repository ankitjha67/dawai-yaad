# Dawai Yaad 💊

**Open-source family health platform — never miss a medicine again.**

100% Free · Unlimited Medicines · Multi-Family Profiles · Hospital/Nurse Integration · SOS Emergency Alerts

Built for Indian families. Works everywhere.

---

## Why Dawai Yaad?

Existing apps (Medisafe, MyTherapy, EveryDose) have critical problems:
- **Paywalls** — Medisafe limits free users to 2 medicines
- **Confusing UI** — Too many menus for elderly users
- **Unreliable notifications** — MyTherapy randomly stops alerting
- **No India focus** — Meal-based scheduling, Hindi support, Indian pharmacy context
- **No hospital integration** — Nurses can't track patients' medications

Dawai Yaad solves all of these. Forever free. Open source.

## Features

### For Patients & Families
- Unlimited medicine reminders with 12 meal-time slots
- Syrup (ml/tsp/tbsp), ointment (body area), injection (site rotation) support
- Every frequency: daily, alternate, Mon/Wed/Fri, weekly, monthly, quarterly, yearly, every-few-hours, as-needed
- Stock tracking with refill alerts (auto-decrements on dose taken)
- Health measurements: BP, blood sugar, weight, temperature, pulse, SpO2
- Mood tracking & symptom logging
- Privacy mode — hide medicine names from prying eyes
- Multi-family profiles: Papa, Mummy, Dadi, Nana, Chacha, Mausi...
- Doctor report generation (PDF) with adherence charts

### For Caregivers
- Add/edit medicines for family members remotely
- Receive instant alerts when doses are missed
- SOS emergency alerts with real-time notification
- View adherence reports for all family members

### For Hospitals & Nurses
- Assign nurses to patients (ward + bed number)
- Nurse dose administration logging
- Upload blood reports, prescriptions, X-rays
- Generate ward-level adherence reports
- Share reports with doctors

### SOS Emergency
- One-tap SOS with confirmation dialog
- Critical push notifications to ALL caregivers
- Real-time WebSocket alerts
- Acknowledge → Resolve workflow
- Location sharing

## Tech Stack (100% Open Source)

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) + SQLAlchemy |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis |
| Task Scheduler | Celery |
| Push Notifications | Firebase Cloud Messaging |
| File Storage | MinIO (S3-compatible) |
| Mobile App | Flutter |
| Web Dashboard | Next.js |
| Auth | JWT + Phone OTP |
| Deployment | Docker Compose |

## Quick Start

```bash
# Clone
git clone https://github.com/ankitjha67/dawai-yaad.git
cd dawai-yaad

# Copy environment
cp .env.example .env

# Start everything
docker-compose up -d

# API docs at http://localhost:8000/docs
```

## Project Structure

```
dawai-yaad/
├── backend/          # FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic validation
│   │   ├── services/ # Business logic
│   │   ├── tasks/    # Celery background tasks
│   │   └── utils/    # Auth, helpers
│   ├── alembic/      # Database migrations
│   └── tests/        # Pytest test suite
├── mobile/           # Flutter app (Sessions 7-9)
├── web/              # Next.js dashboard (Session 10)
└── docker-compose.yml
```

## API Documentation

Start the server and visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/send-otp` | Send OTP to phone |
| POST | `/api/v1/auth/verify-otp` | Verify & get JWT tokens |
| GET | `/api/v1/medications` | List medications |
| POST | `/api/v1/medications` | Add medication |
| POST | `/api/v1/medications/{id}/taken` | Mark dose taken |
| GET | `/api/v1/medications/schedule/today` | Today's schedule |
| GET | `/api/v1/medications/stock/low` | Low stock alerts |
| POST | `/api/v1/health/measurements` | Log BP/sugar/weight |
| POST | `/api/v1/health/moods` | Log mood |
| POST | `/api/v1/health/symptoms` | Log symptoms |
| POST | `/api/v1/sos/trigger` | Trigger SOS emergency |
| PUT | `/api/v1/sos/{id}/acknowledge` | Acknowledge SOS |
| WS | `/api/v1/sos/ws/{user_id}` | Real-time SOS WebSocket |

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pip install aiosqlite pytest-asyncio
pytest tests/ -v
```

## Deployment (India)

Works on any VPS with Docker:

| Provider | Region | Cost |
|----------|--------|------|
| Hetzner | Finland/India | ~₹800/mo |
| DigitalOcean | Bangalore | ~₹1,200/mo |
| AWS | Mumbai (ap-south-1) | ~₹1,500/mo |

## Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE)

## Author

**Ankit Jha** — [@ankitjha67](https://github.com/ankitjha67)

Built with love for Indian families. 🇮🇳
