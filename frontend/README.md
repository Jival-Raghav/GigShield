## Raah Saathi Quickstart

Use this guide if you are handing off the project to a teammate.

No code changes are required to run the current demo flow.

---

## 1) Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (recommended for Postgres + Redis)

---

## 2) Start Infra (Postgres + Redis)

From the backend folder:

```powershell
cd backend
docker compose up -d
```

This starts:

- Postgres on localhost:55432
- Redis on localhost:6379

---

## 3) Backend Setup and Run

From backend folder:

```powershell
cd backend

# create venv (first time only)
python -m venv .venv

# activate venv
.\.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run migrations
alembic upgrade head

# seed demo data
python -m db.seed_data

# run backend
uvicorn main:app --reload --port 8000
```

Backend URLs:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 4) Frontend Setup and Run

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- App: http://localhost:3000

If frontend does not start, run:

```powershell
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## 5) Demo Login Users

Seeded users:

- Ravi Kumar: +919876543210
- Priya Sharma: +919876543211
- Suresh Reddy: +919876543212

OTP is mocked in dev. Read it from:

- backend terminal line starting with [OTP-MOCK]
- or otp_debug field in OTP request response when DEBUG=true

---

## 👥 Test Users

After running `seed_data.py`, these test users are available:

| Name | Phone | Zone | Platform |
|------|-------|------|----------|
| Ravi Kumar | +919876543210 | BLR_KORAMANGALA_004 | swiggy |
| Priya Sharma | +919876543211 | PUN_KOTHRUD_002 | zomato |
| Suresh Reddy | +919876543212 | HYD_GACHIBOWLI_007 | uber |

**Login:** Use any phone number → OTP is shown in console (DEBUG=True)

---

## 🔄 Complete User Flows

### Worker Flow

1. **Login**
   - Enter phone number → Request OTP
   - Enter OTP (shown in console in debug mode)
   - Redirected to dashboard

2. **View Dashboard**
   - See trust score, active policy, recent claims
   - Monitor active disruptions in your zone

3. **Buy Insurance**
   - Go to Premium tab → Compute baseline income
   - Compare Basic/Standard/Premium tiers
   - Select tier and create policy

4. **Monitor Disruptions**
   - View active disruptions in your zone
   - Simulate disruption (dev mode)

5. **File a Claim**
   - Go to Claims tab
   - Select active policy and disruption
   - Submit claim → View BAF score and payout

6. **Track Payouts**
   - View claim status (pending → approved → paid)
   - See total payouts on dashboard

### Admin Flow

1. **Login** (same as worker)

2. **View Dashboard**
   - Total active policies, claims today, payouts
   - Loss ratio, average BAF score
   - Quick view of flagged claims

3. **Review Flagged Claims**
   - Go to Flagged Claims tab
   - View claim details, BAF score, signals
   - Approve or Reject claims

4. **Initiate Payouts**
   - For approved claims, click "Initiate Payout"
   - Claim status changes to "Paid"
   - Worker sees payout on their dashboard

5. **Monitor Zone Risk**
   - View zones with most disruptions
   - See severity trends

---

## 🔧 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/otp/request` | Request OTP for phone |
| POST | `/auth/otp/verify` | Verify OTP, get token |

### Workers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/workers/register` | Register new worker |
| GET | `/workers/{id}` | Get worker details |
| PUT | `/workers/{id}` | Update worker |

### Premium & Policies
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/baseline/compute/{worker_id}` | Compute baseline income |
| POST | `/premium/quote` | Get premium quote |
| POST | `/policies/create` | Create policy |
| GET | `/policies/{worker_id}` | List worker's policies |

### Triggers & Disruptions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/triggers/check` | Check for disruptions |
| POST | `/triggers/simulate` | Simulate disruption (dev) |
| GET | `/triggers/active/{zone_id}` | Get active disruptions |

### Claims
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/claims/initiate` | Initiate new claim |
| GET | `/claims/{id}` | Get claim details |
| GET | `/claims/worker/{id}` | List worker's claims |
| POST | `/claims/{id}/status` | Update claim status |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/dashboard` | Get admin metrics |
| GET | `/admin/claims/flagged` | List flagged claims |
| GET | `/admin/zones/risk` | Get zone risk data |
| POST | `/admin/claims/{id}/status` | Admin update claim |

### Payouts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payouts/{claim_id}/initiate` | Initiate payout |

---

## 🎨 Frontend Implementation Summary

### What We Built

1. **Authentication System**
   - OTP-based login flow (request → verify → store token)
   - AuthContext for global auth state
   - Protected routes with auto-redirect
   - Token expiration handling

2. **Centralized API Layer**
   - Axios instance with base URL configuration
   - Request interceptor adds Bearer token
   - Response interceptor handles 401 errors
   - All API functions in single `api.ts` file

3. **Data Fetching with TanStack Query**
   - Custom hooks for each data domain
   - Automatic caching and refetching
   - Polling intervals for real-time feel
   - Optimistic updates for mutations

4. **Component Architecture**
   - shadcn/ui for consistent design
   - Reusable common components (StatusBadge, StatCard, etc.)
   - Layout wrappers for worker/admin
   - Mobile-first responsive design

5. **Worker Dashboard**
   - Stats cards (trust score, payouts, policies)
   - Active disruption alerts
   - Recent claims list
   - Quick navigation

6. **Premium Calculator**
   - Baseline income computation
   - Tier comparison (Basic/Standard/Premium)
   - Visual confidence indicators
   - One-click policy creation

7. **Claims Management**
   - Initiate claim with policy/disruption selection
   - Real-time status tracking
   - BAF score visualization
   - Payout details modal

8. **Admin Dashboard**
   - KPI cards with live data
   - Flagged claims table
   - One-click approve/reject
   - Payout initiation
   - Zone risk charts

---

## 🐛 Troubleshooting

### PostgreSQL Permission Denied
```sql
-- Connect as postgres superuser
psql -U postgres -d gigshield

-- Grant permissions
GRANT ALL ON SCHEMA public TO gigshield;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gigshield;
```

### Alembic Migration Conflict
```bash
# If tables already exist manually
alembic stamp head
```

### Port Already in Use
```bash
# Kill process on port 8000 (macOS/Linux)
lsof -ti:8000 | xargs kill -9

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Redis Connection Error
Redis is optional. The app works without it, but caching will be disabled.