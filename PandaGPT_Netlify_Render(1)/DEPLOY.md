# PandaGPT deployment

## 1. GitHub
Upload `frontend/` and `backend/` to a GitHub repository. Never upload a real API key.

## 2. Render backend
Create a Render Web Service from the repo.
Root Directory: `backend`
Build Command: `pip install -r requirements.txt`
Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Environment:
- OPENAI_API_KEY = your OpenAI API key
- AI_MODEL = gpt-5.5
- AI_NAME = PandaGPT
- CORS_ORIGINS = your Netlify URL

Test: `https://YOUR-RENDER-SERVICE.onrender.com/health`

## 3. Netlify frontend
Import the same GitHub repo.
Base directory: `frontend`
Build command: `npm run build`
Publish directory: `dist`
Environment:
`VITE_API_URL=https://YOUR-RENDER-SERVICE.onrender.com`

Deploy. Then set the exact Netlify URL as Render's `CORS_ORIGINS` and redeploy Render.

## Security
Keep OPENAI_API_KEY only on Render.

## Database
The starter uses SQLite. For persistent production memory, use Postgres rather than local service storage.
