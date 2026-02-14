# Deploy EcoPackAI to Render

This guide will help you deploy your EcoPackAI application to Render's free tier.

## Prerequisites

- Your code is now pushed to GitHub: `https://github.com/ankit-5002/Eco-Pack_AI`
- A Render account (sign up at https://render.com)

## Deployment Steps

### 1. Create a New Web Service

1. Go to https://render.com and log in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if you haven't already
4. Select the repository: `ankit-5002/Eco-Pack_AI`

### 2. Configure the Web Service

Use the following settings:

- **Name**: `ecopackai` (or your preferred name)
- **Region**: Choose the region closest to you
- **Branch**: `main`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### 3. Set Environment Variables

Click **"Advanced"** and add these environment variables:

| Key | Value |
|-----|-------|
| `PYTHON_VERSION` | `3.11.0` |
| `DATABASE_URL` | Your PostgreSQL connection string (if using database) |

> **Note**: If you're using Supabase or another PostgreSQL database, add the connection string here.

### 4. Configure Free Tier Settings

- **Instance Type**: Select **"Free"**
- **Auto-Deploy**: Enable this to automatically deploy when you push to GitHub

### 5. Deploy

1. Click **"Create Web Service"**
2. Render will start building and deploying your application
3. Monitor the logs for any errors
4. Once deployed, you'll get a URL like: `https://ecopackai.onrender.com`

## Important Notes

### Memory Optimization

The free tier has **512 MB RAM** limit. Your app is configured with lazy loading for ML models to stay within this limit.

### Auto-Sleep

Free tier services sleep after 15 minutes of inactivity. The first request after sleep will take longer (cold start ~30-60 seconds).

### Database

If you need a database:
1. In Render dashboard, click **"New +"** → **"PostgreSQL"**
2. Create a free PostgreSQL instance
3. Copy the **External Database URL**
4. Add it as `DATABASE_URL` environment variable in your web service

## Troubleshooting

### Out of Memory Error

If you get memory errors:
- Ensure lazy loading is enabled in `app.py`
- Consider using external model hosting (e.g., HuggingFace Inference API)

### Build Failures

Check that:
- `requirements.txt` is up to date
- All dependencies are compatible with Python 3.11

### Application Not Starting

- Check the logs in Render dashboard
- Verify the start command is correct: `gunicorn app:app`
- Ensure Flask app is named `app` in `app.py`

## Next Steps

After deployment:
1. Test all endpoints
2. Monitor memory usage in Render dashboard
3. Set up custom domain (optional, available on paid plans)

## Useful Links

- Render Documentation: https://render.com/docs
- Your GitHub Repo: https://github.com/ankit-5002/Eco-Pack_AI
- Render Dashboard: https://dashboard.render.com
