# Deploy Coursewise: Render + Supabase

This guide publishes the full Coursewise application from one URL. Flask serves
the compiled React dashboard, so sign-in cookies remain simple and secure.

## 1. Put the project on GitHub

Create an empty GitHub repository named `coursewise`, then run these commands
in the Coursewise folder. Do not add `.env` or `coursewise.db` to GitHub.

```bash
git init
git add .
git commit -m "Prepare Coursewise for deployment"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## 2. Create the Supabase database

1. Create a free project at https://supabase.com/dashboard.
2. Open **Connect** and copy the **Session pooler** connection string.
3. Replace the password placeholder in that string with the database password.
4. Keep the complete string private. It becomes the `DATABASE_URL` value on
   Render. Never add it to `.env` files that will be pushed to GitHub.

Coursewise creates its tables automatically the first time it connects to the
empty PostgreSQL database.

## 3. Deploy on Render

1. Create an account at https://render.com.
2. Choose **New** → **Blueprint** and select the GitHub repository.
3. Render detects `render.yaml`. Create the service on the Free plan.
4. In the service environment settings, add the following private values:

```text
DATABASE_URL=your-private-supabase-session-pooler-url
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://YOUR_RENDER_URL/api/auth/google/callback
FRONTEND_URL=https://YOUR_RENDER_URL
```

5. Save the values and redeploy. Open the Render URL and check `/api/health`.

## 4. Update Google OAuth

In Google Cloud Console, open the Coursewise OAuth web client. Under
**Authorised redirect URIs**, add exactly:

```text
https://YOUR_RENDER_URL/api/auth/google/callback
```

Use the exact URL displayed by Render. Keep the existing localhost callback so
Google sign-in keeps working during local development.

## 5. Final checks

- Register an email/password account.
- Sign in with the Google account listed as a Google test user.
- Search for a course.
- Save, enrol in, and complete a course.
- Refresh the page and confirm the profile and activity remain.

## Free-tier notes

Render's free service may sleep after inactivity. Supabase free projects may
also pause when inactive. These services are suitable for a demonstration;
use paid plans and regular backups before accepting long-term public user data.

The local Ollama/Qwen explanation model does not run inside this free cloud
deployment. The app continues to work with its built-in safe explanation until
a cloud AI provider or dedicated Ollama server is added.
