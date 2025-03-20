PROJECT_ID=$1
docker buildx build --platform linux/amd64 -t gcr.io/$PROJECT_ID/fastapi-app .
docker push gcr.io/$PROJECT_ID/fastapi-app
gcloud run deploy fastapi-app \
  --image gcr.io/$PROJECT_ID/fastapi-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated