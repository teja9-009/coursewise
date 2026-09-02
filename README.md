# Coursewise

Coursewise is a full-stack course recommendation app. It searches a real combined Coursera and Udemy catalog, ranks courses with TF-IDF and cosine similarity, and uses a local Qwen model through Ollama to explain the best recommendation in plain language.

## Features

- Search a combined Coursera and Udemy course catalog
- Filter recommendations by platform, level, and category
- Rank recommendations with TF-IDF, cosine similarity, quality signals, and learner preferences
- Explain the top course recommendation using local Qwen through Ollama
- Create an account and stay signed in across browser refreshes
- Save courses and mark courses as enrolled or completed
- Keep a learner profile with current level, skills, learning goal, and status
- Store search history and learner activity in SQLite
- Use a React, Tailwind, and shadcn/ui dashboard connected to a Flask API

## Technology

| Layer | Tool |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS, shadcn/ui |
| Backend | Flask, Flask-Login, Flask-SQLAlchemy |
| Database | SQLite |
| Recommendations | scikit-learn TF-IDF and cosine similarity |
| AI explanations | Ollama with `qwen3.5:9b` |
| Data | Coursera and Udemy CSV files |

## Project structure

```text
course-recommender/
├── app/                 Flask API, database models, and legacy Flask pages
├── data/                Coursera, Udemy, combined, and cleaned datasets
├── recommendation/      TF-IDF recommender and ranking code
├── frontend/            React dashboard
├── run.py               Flask entry point
├── requirements.txt     Python dependencies
└── coursewise.db        Local SQLite database, created automatically
```

## Run the project

### 1. Start Ollama

Make sure Ollama is running and the Qwen model is installed:

```bash
ollama pull qwen3.5:9b
```

### 2. Start the Flask backend

Open a terminal in the project folder:

```bash
cd /Users/saiteja/course-recommender
source .venv/bin/activate
python run.py
```

The backend runs at `http://127.0.0.1:5000`.

### 3. Start the React dashboard

Open a second terminal:

```bash
cd /Users/saiteja/course-recommender/frontend
npm run dev
```

Open the URL Vite prints, normally `http://localhost:5173`.

## Run the automated checks

With the virtual environment active, run:

```bash
pytest -q
```

These tests use a temporary database. They check account registration, login state,
learner-profile updates, recommendations, and saved/enrolled/completed course tracking
without changing your real Coursewise data.

## Persistent login session

Coursewise reads its private session key from the local `.env` file automatically.
The file is excluded from GitHub, so never share or commit it. This keeps users signed in
across normal Flask restarts during local development.

## Google sign-in setup

Coursewise has a Google sign-in button, but it remains inactive until you add your own
Google OAuth credentials. In Google Cloud Console, create an OAuth client with the type
**Web application**. Add this exact authorised redirect URI:

```text
http://localhost:5000/api/auth/google/callback
```

Then add the client ID and client secret to the private `.env` file:

```text
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

Restart Flask after saving the file. Google requires the redirect URI to match the value
in Google Cloud Console exactly.

## Future research phase

After enough real saved, enrolled, and completed-course activity is collected, the project can add:

- GRU4Rec for sequence-based recommendations
- SHAP for trained engagement-model explanations
- Contrastive learning for richer user-course representations
