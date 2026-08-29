# Smart Trafik - Complete Setup Script
# Run in PowerShell as Administrator

$ProjectRoot = "C:\Users\RAM1\Documents\Smart Traffic"
Set-Location -LiteralPath $ProjectRoot

Write-Host "=== Smart Trafik Deployment Setup ===" -ForegroundColor Green

# 1. Check prerequisites
Write-Host "`n1. Checking prerequisites..." -ForegroundColor Yellow

$hasGcloud = Get-Command gcloud -ErrorAction SilentlyContinue
$hasGit = Get-Command git -ErrorAction SilentlyContinue
$hasNode = Get-Command node -ErrorAction SilentlyContinue
$hasFirebase = Get-Command firebase -ErrorAction SilentlyContinue

if (-not $hasGcloud) { Write-Warning "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install" }
if (-not $hasGit) { Write-Warning "git not found. Install: https://git-scm.com/" }
if (-not $hasNode) { Write-Warning "Node.js not found. Install: https://nodejs.org/" }
if (-not $hasFirebase) { Write-Warning "firebase-tools not found. Run: npm install -g firebase-tools" }

# 2. Create .env.production for frontend
Write-Host "`n2. Creating production env file..." -ForegroundColor Yellow
@"
# Production API URL - UPDATE AFTER CLOUD RUN DEPLOY
VITE_API_BASE_URL=https://smart-trafik-api-xxxxx-uc.a.run.app
"@ | Set-Content -Path "$ProjectRoot\frontend\.env.production" -Encoding UTF8

# 3. Update frontend to use env var
Write-Host "3. Updating frontend to use environment variable..." -ForegroundColor Yellow
$frontendHtml = Get-Content -Path "$ProjectRoot\frontend\index.html" -Raw
$frontendHtml = $frontendHtml -replace 'const API_BASE_URL="http://127\.0\.0\.1:8000"', 'const API_BASE_URL=import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"'
$frontendHtml | Set-Content -Path "$ProjectRoot\frontend\index.html" -Encoding UTF8

# 4. Add vite config for env
Write-Host "4. Adding Vite config..." -ForegroundColor Yellow
@"
import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  publicDir: false,
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true
  },
  server: {
    port: 5500,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/video-feed': 'http://127.0.0.1:8000'
    }
  }
})
"@ | Set-Content -Path "$ProjectRoot\frontend\vite.config.js" -Encoding UTF8

# 5. Update firebase.json to use built output
Write-Host "5. Updating firebase.json for build output..." -ForegroundColor Yellow
$firebaseJson = @{
  firestore = @{
    rules = "firestore.rules"
    indexes = "firestore.indexes.json"
  }
  hosting = @{
    public = "frontend-dist"
    ignore = @("firebase.json", "**/.*", "**/node_modules/**")
    rewrites = @(@{ source = "**"; destination = "/index.html" })
  }
} | ConvertTo-Json -Depth 5
$firebaseJson | Set-Content -Path "$ProjectRoot\firebase.json" -Encoding UTF8

# 6. Create package.json for frontend
Write-Host "6. Creating frontend package.json..." -ForegroundColor Yellow
@{
  name = "smart-trafik-frontend"
  version = "1.0.0"
  type = "module"
  scripts = @{
    dev = "vite"
    build = "vite build"
    preview = "vite preview"
    deploy = "npm run build && firebase deploy --only hosting"
  }
  devDependencies = @{
    vite = "^5.0.0"
  }
} | ConvertTo-Json -Depth 5 | Set-Content -Path "$ProjectRoot\frontend\package.json" -Encoding UTF8

# 7. GitHub repo creation instructions
Write-Host "`n=== MANUAL STEPS REQUIRED ===" -ForegroundColor Red
Write-Host "`n7. Create GitHub repo:" -ForegroundColor Cyan
Write-Host "   Go to https://github.com/new"
Write-Host "   Repo name: smart-trafik"
Write-Host "   Don't initialize with README/license/gitignore"

Write-Host "`n8. Push to GitHub:" -ForegroundColor Cyan
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/smart-trafik.git"
Write-Host "   git branch -M main"
Write-Host "   git push -u origin main"

Write-Host "`n9. Create GCP Service Account (run in Cloud Shell or local with gcloud):" -ForegroundColor Cyan
@"
gcloud iam service-accounts create github-deploy --display-name="GitHub Deploy"
gcloud projects add-iam-policy-binding smart-traffic-dab1e \
  --member="serviceAccount:github-deploy@smart-traffic-dab1e.iam.gserviceaccount.com" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding smart-traffic-dab1e \
  --member="serviceAccount:github-deploy@smart-traffic-dab1e.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"
gcloud projects add-iam-policy-binding smart-traffic-dab1e \
  --member="serviceAccount:github-deploy@smart-traffic-dab1e.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
gcloud iam service-accounts keys create key.json --iam-account=github-deploy@smart-traffic-dab1e.iam.gserviceaccount.com
"@

Write-Host "`n10. Add GitHub Secrets (Settings > Secrets > Actions):" -ForegroundColor Cyan
Write-Host "    GCP_SA_KEY = contents of key.json (from step 9)"
Write-Host "    FIREBASE_TOKEN = run 'firebase login:ci' locally and paste token"

Write-Host "`n11. After first deploy, update frontend/.env.production with actual Cloud Run URL" -ForegroundColor Cyan

Write-Host "`n=== OPTIONAL: Local Development ===" -ForegroundColor Green
Write-Host "cd frontend && npm install && npm run dev"
Write-Host "cd .. && .\run.ps1"

Write-Host "`nDone! Check $ProjectRoot for changes." -ForegroundColor Green