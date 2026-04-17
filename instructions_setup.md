# GigShield Full Setup Instructions (From Scratch)

This guide gets the full project running from zero on a new machine.

## 1. What You Need

1. Git
2. Docker Desktop (with Compose)
3. Node.js 20+ and npm
4. Optional local backend mode: Python 3.13

Recommended OS: Windows 10/11, macOS, or Linux.

## 2. Clone Project

```bash
git clone <your-repo-url>
cd GigShield
```

## 3. Backend Environment File

Copy the example env file and fill required values.

```bash
cd backend
copy .env.example .env
```

If `copy` is not available, use your shell equivalent.

Minimum fields to run local demo:

1. `SECRET_KEY`
2. `DATABASE_URL` (if running non-docker DB)
3. `REDIS_URL` (if running non-docker Redis)

For Docker Compose default setup, database and redis are injected automatically from compose file, but keep `.env` present for all other settings.

## 4. Start Backend + DB + Redis (Docker First)

From `backend` folder:

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"raah-saathi-api"}
```

## 5. Seed Demo Data (Workers, Policies, Disruptions, Claims)

From `backend` folder:

```bash
docker compose exec -T backend python db/seed_data.py
```

This seeds users like Ravi, Ananya, Karthik, Priya, and others used in demo flows.

## 6. Frontend Setup

Open a new terminal at project root:

```bash
cd frontend
npm install
```

Optional frontend env for API URL:

Create `frontend/.env.local` with:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Start frontend:

```bash
npm run dev
```

Open app:

1. `http://localhost:3000`

## 7. Quick Login and Smoke Test

Backend uses OTP flow and returns `otp_debug` for local testing.

Request OTP:

```bash
curl -X POST http://localhost:8000/api/v1/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919876543210"}'
```

Verify OTP (use `otp_debug` from previous response):

```bash
curl -X POST http://localhost:8000/api/v1/auth/otp/verify \
  -H "Content-Type: application/json" \
  -d '{"phone":"+919876543210","otp":"<otp_debug>"}'
```

Use returned `access_token` as Bearer token for protected APIs.

## 8. Run Demo Scenario (Disruption -> Claim -> Auto Pay)

Simulate ended disruption in worker zone:

```bash
curl -X POST http://localhost:8000/api/v1/triggers/simulate \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id":"BLR_KORAMANGALA_NW",
    "disruption_type":"rainfall",
    "severity":0.82,
    "signal_source":"MANUAL_SIMULATION",
    "started_at":"2026-04-17T12:00:00Z",
    "ended_at":"2026-04-17T17:00:00Z"
  }'
```

Check claim list:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/v1/claims/worker/<worker_id>
```

Check wallet/total paid:

```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8000/api/v1/workers/<worker_id>/wallet
```

## 9. Admin Demo Checks

Login with admin-enabled seeded/testing account and call:

```bash
curl -H "Authorization: Bearer <admin_token>" \
  "http://localhost:8000/api/v1/admin/claims/flagged?limit=25&offset=0"
```

## 10. Optional LLM Configuration (Groq/OpenAI-Compatible)

In `backend/.env`:

```env
GROQ_API_KEY=<your_key>
NEWS_LLM_ENABLED=true
FRAUD_LLM_ENABLED=true
NEWS_LLM_MODEL=llama-3.1-8b-instant
FRAUD_LLM_MODEL=llama-3.1-8b-instant
NEWS_LLM_ENDPOINT=https://api.groq.com/openai/v1/chat/completions
FRAUD_LLM_ENDPOINT=https://api.groq.com/openai/v1/chat/completions
```

If LLM endpoint fails, app falls back to template-style explanation behavior in some flows.

## 11. Optional: Rebuild ML Risk Model

Pretrained model files already exist in `backend/ml/`.

To retrain manually:

```bash
cd backend
python ml/train_risk_model.py
```

## 12. Stop and Restart

Stop stack:

```bash
cd backend
docker compose down
```

Restart stack:

```bash
cd backend
docker compose up -d
```

## 13. Common Issues and Fixes

1. Backend not responding right after restart:
   wait until dependency install finishes, then retry `/health`.
2. Frontend cannot call backend:
   verify `NEXT_PUBLIC_API_URL` and backend running on port 8000.
3. OTP/admin calls unauthorized:
   confirm Bearer token from latest OTP verify response.
4. Empty demo data:
   run `docker compose exec -T backend python db/seed_data.py` again.
5. Stale container code behavior:
   run `docker compose restart backend`.

## 14. One-Command Demo Bring-Up (After Clone)

Run from `backend` folder first:

```bash
copy .env.example .env
docker compose up -d
docker compose exec -T backend python db/seed_data.py
```

Then from `frontend` folder:

```bash
npm install
npm run dev
```

You are ready to demo at `http://localhost:3000` with backend at `http://localhost:8000`.
