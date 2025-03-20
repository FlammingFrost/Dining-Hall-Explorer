gcloud services enable cloudscheduler.googleapis.com
gcloud run services describe fastapi-app --region us-central1 --format 'value(status.url)'

gcloud scheduler jobs create http db-update-every-2-hours \
  --schedule="0 */2 * * *" \
  --time-zone="UTC" \
  --uri="https://fastapi-app-902489793845.us-central1.run.app/update-database" \
  --http-method=POST \
  --location=us-central1 \
  --description="Run database update every 2 hours"

gcloud scheduler jobs list --location=us-central1
gcloud scheduler jobs run db-update-every-2-hours --location=us-central1