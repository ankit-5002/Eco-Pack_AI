# EcoPackAI - Google Cloud Run Deployment Guide

## Quick Start (Recommended)

Run these commands in Google Cloud Shell after uploading and extracting your project:

```bash
cd EcoPackAI2

# Step 1: Build the container
gcloud builds submit --tag gcr.io/eco-pack-ai-web/ecopackai

# Step 2: Deploy to Cloud Run
gcloud run deploy ecopackai \
  --image gcr.io/eco-pack-ai-web/ecopackai \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --port 8080 \
  --set-env-vars ENVIRONMENT=production,PORT=8080 \
  --max-instances 10 \
  --min-instances 0
```

## Alternative: Deploy with Database

If you want to use Supabase PostgreSQL:

```bash
# Replace [PASSWORD] and [PROJECT-REF] with your Supabase credentials
gcloud run deploy ecopackai \
  --image gcr.io/eco-pack-ai-web/ecopackai \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --port 8080 \
  --set-env-vars ENVIRONMENT=production,PORT=8080,DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
```

## Using service.yaml (Declarative)

If you prefer using the configuration file:

```bash
# Build first
gcloud builds submit --tag gcr.io/eco-pack-ai-web/ecopackai

# Deploy using service.yaml
gcloud run services replace service.yaml --region us-central1
```

## Verify Deployment

```bash
# Get service URL
gcloud run services describe ecopackai --region us-central1 --format 'value(status.url)'

# Test health endpoint
curl $(gcloud run services describe ecopackai --region us-central1 --format 'value(status.url)')/health

# View logs
gcloud run services logs read ecopackai --region us-central1 --limit 50
```

## Troubleshooting

### If build fails
```bash
# Check build logs
gcloud builds list --limit 5
gcloud builds log [BUILD_ID]
```

### If deployment fails
```bash
# Check service status
gcloud run services describe ecopackai --region us-central1

# Update gcloud CLI
gcloud components update

# Try with more memory
gcloud run services update ecopackai --memory 2Gi --region us-central1
```

### Common Issues

1. **"Revision failed to become ready"**
   - Check logs: `gcloud run services logs read ecopackai --region us-central1 --limit 100`
   - Increase memory to 2Gi
   - Verify models directory exists

2. **"Container failed to start"**
   - Check health endpoint is accessible at `/health`
   - Verify PORT environment variable is set to 8080
   - Check startup logs for missing dependencies

3. **"gcloud crashed" error**
   - Use two-step build→deploy process (recommended approach above)
   - Update gcloud: `gcloud components update`
   - Clear cache: `gcloud config unset project && gcloud config set project eco-pack-ai-web`

## Configuration Files

The following files are configured for Cloud Run:

- **Dockerfile**: Container configuration with Python 3.11, gunicorn, and optimized for Cloud Run
- **service.yaml**: Cloud Run service specification with health checks
- **.gcloudignore**: Excludes unnecessary files from deployment
- **.dockerignore**: Excludes files from Docker build context

## Resource Limits

Current configuration:
- Memory: 1 GB (can increase to 2 GB if needed)
- CPU: 1 vCPU
- Timeout: 300 seconds
- Max instances: 10 (auto-scales based on traffic)
- Min instances: 0 (scales to zero when idle - free tier friendly)

## Costs

With current configuration:
- **Free tier**: 2 million requests/month, 360,000 GB-seconds/month
- Your app should stay within free tier with moderate usage
- Scales to zero when not in use (no charges)

## Next Steps

After successful deployment:

1. Note your service URL from the output
2. Test the application in your browser
3. Set up a custom domain (optional):
   ```bash
   gcloud run domain-mappings create --service ecopackai --domain your-domain.com --region us-central1
   ```

## Support

For detailed troubleshooting, see: `cloud_run_deployment_fix.md`
