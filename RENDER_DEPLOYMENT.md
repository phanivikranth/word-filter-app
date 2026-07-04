# 🚀 Deployment Guide: Cloudflare Pages & Render

This guide outlines the step-by-step procedure to deploy the Word Filter application live using **Cloudflare Pages** for the frontend and **Render** for the backend FastAPI service.

---

## 🛠️ Step 1: Deploy Backend to Render (FastAPI)

Render can build and run your backend directly from your GitHub repository using the `render.yaml` Blueprint file we created.

### 1.1 Deploy with Render Blueprint

1. Go to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** in the top right corner and select **Blueprint**.
3. Connect your GitHub repository (`word-filter-app`).
4. Render will automatically detect the `render.yaml` file in the root directory.
5. Review the service config:
   - **Service Name**: `word-filter-backend`
   - **Environment**: `Docker`
   - **Plan**: `Free`
6. Click **Apply**.
7. Wait for Render to finish building the Docker image and deploy the container. Once deployed, you will see a service URL like `https://word-filter-backend.onrender.com`.

---

## 🌐 Step 2: Configure Frontend Routing

Since we are deploying frontend and backend to different domains, we use a Cloudflare rewrite rule to proxy requests from the frontend to the backend.

### 2.1 Update the Proxy Redirect URL

Once your backend is successfully deployed and you have your Render URL (e.g., `https://word-filter-backend.onrender.com`):

1. Open `frontend/public/_redirects`.
2. Locate the following rule:
   ```text
   /api/* https://api.example.com/:splat 200
   ```
3. Update `https://api.example.com` with your real Render URL:
   ```text
   /api/* https://word-filter-backend.onrender.com/:splat 200
   ```
4. Commit and push this change to your GitHub repository.

---

## ⚡ Step 3: Deploy Frontend to Cloudflare Pages

Cloudflare Pages can build and deploy the Angular frontend automatically.

1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Navigate to **Workers & Pages** > **Create application** > **Pages** > **Connect to Git**.
3. Select your GitHub repository (`word-filter-app`) and click **Begin setup**.
4. Configure the build settings:
   - **Project name**: `word-filter-app`
   - **Production branch**: `main`
   - **Framework preset**: `Angular`
   - **Build command**: `npm run build`
   - **Build output directory**: `frontend/dist/word-filter-frontend`
   - **Root directory**: `frontend`
5. Click **Save and Deploy**.
6. Cloudflare will clone your repository, build the Angular project, copy static assets (including `_redirects` and `_headers`), and deploy them.

---

## ✅ Verification & Health Checks

Once both services are deployed, you can verify they are working:

1. Visit your Cloudflare Pages URL (e.g., `https://word-filter-app.pages.dev`).
2. Test the word filtering tabs, word list statistics, and interactive puzzle solver.
3. Open your browser DevTools (F12) > Network Tab, and check that API calls are being routed to `/api/words` and returning `200 OK` successfully.
