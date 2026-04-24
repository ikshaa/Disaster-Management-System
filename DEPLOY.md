# Deploying Rescue-AI to Render

Two services need to be deployed:
1. **Backend** (Python FastAPI) — hosts the AI hub
2. **Frontend** (React + Vite) — static dashboard site

The repo includes `render.yaml` so Render can deploy both automatically.

---

## Step 1 — Push everything to GitHub (already done)

Repo: `https://github.com/gsam99/Disaster-Management-System` · branch `feature/ai-models`

Verify both teammates have access. The repo includes:
- `backend/` — FastAPI server with all AI code
- `frontend/` — React dashboard with environment-aware API URLs
- `render.yaml` — Render Blueprint (auto-deploys both services)
- `backend/runtime.txt` — pins Python 3.11

---

## Step 2 — Deploy via Render Blueprint (Samhita does this on her account)

1. Log in at **https://dashboard.render.com**
2. Click **New** → **Blueprint**
3. Connect the GitHub repo `gsam99/Disaster-Management-System`
4. Select the branch `feature/ai-models`
5. Render reads `render.yaml` and shows two services:
   - `rescue-ai-backend` (Python web service)
   - `rescue-ai-frontend` (Static site)
6. Click **Apply**

Render will:
- Install backend Python dependencies (~3 minutes)
- Build the React frontend (~2 minutes)
- Assign URLs like:
  - `https://rescue-ai-backend.onrender.com`
  - `https://rescue-ai-frontend.onrender.com`

---

## Step 3 — Connect frontend to backend

Once the backend is deployed and you have its URL:

1. Go to **rescue-ai-frontend** service in Render dashboard
2. Click **Environment** tab
3. Add environment variable:
   ```
   VITE_API_URL = https://rescue-ai-backend.onrender.com
   ```
   (use the actual backend URL from step 2)
4. Click **Manual Deploy** → **Deploy latest commit** to rebuild with the new variable

---

## Step 4 — Open the deployed dashboard

```
https://rescue-ai-frontend.onrender.com           ← responder dashboard
https://rescue-ai-frontend.onrender.com/citizen   ← citizen form
https://rescue-ai-backend.onrender.com/docs       ← API docs
```

---

## Important notes about the deployed version

### Models are NOT deployed automatically
The DistilBERT (267MB) and ResNet50 (210MB) weights are too large for git and not included in the deploy. The system handles this gracefully:

| Model | Without weights | Effect |
|-------|----------------|--------|
| DistilBERT NLP | Falls back to keyword classifier | Works fine — slightly less accurate |
| ResNet50 Vision | Returns image_score = 0 | Vision analysis disabled — text-only scoring |

So the deployed app:
- ✅ Accepts reports (text + GPS + optional image)
- ✅ Classifies text via keywords
- ✅ Computes priority scores (text × 0.8 + location × 0.2)
- ✅ Live dashboard with map and WebSocket
- ❌ Does not analyze images (fallback gives 0 score)

To enable models in production, either:
- Upload weights to S3/HuggingFace Hub and download on container start
- Use Render persistent disk (paid plan)

### Database is ephemeral
Render's free tier has an ephemeral filesystem — SQLite resets on every redeploy. For demo this is fine. For production, switch to PostgreSQL:
1. Create Render PostgreSQL instance
2. Update `backend/db/database.py` to use `DATABASE_URL` env var
3. Add `DATABASE_URL` to backend service env vars (Render auto-injects this when you link a database)

### Free tier sleeps after 15 min idle
First request after sleep takes ~30-50 seconds to wake up. Upgrade to paid for always-on.

### Mesh relay is NOT deployed
The mesh relay (`mesh/relay.py`) is meant to run on edge devices, not the cloud. Run it locally on a laptop for the demo.

---

## Local development still works

Nothing changes for local dev. The frontend automatically detects:
- `VITE_API_URL` set → use that (production)
- Not set → use `/api/v1` proxy to localhost (dev)

Just `bash start.sh` as before.
