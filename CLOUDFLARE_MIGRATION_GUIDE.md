# 🚀 Enterprise-Level Cloudflare Migration Guide
## From CIVO Kubernetes to Cloudflare + Modern PaaS

**Author**: Senior DevOps Engineer  
**Version**: 2.0.0  
**Status**: Enterprise Production-Ready  
**Date**: 2026-06-18

---

## 📋 Executive Summary

This guide provides a **complete architectural transformation** from CIVO Kubernetes to a **serverless-first, globally distributed, enterprise-grade infrastructure** using Cloudflare, Railway/Fly.io, and modern DevOps practices.

### Why Cloudflare?
✅ **Global Distribution**: Automatic worldwide CDN  
✅ **Security**: Built-in DDoS protection, WAF, rate limiting  
✅ **Reliability**: 99.97% SLA with failover  
✅ **Cost**: Pay-as-you-go, no infrastructure overhead  
✅ **Performance**: Sub-50ms global latency  
✅ **Zero Cold Starts**: With proper caching strategy  
✅ **Enterprise Features**: Workers, KV, D1, R2, Durable Objects  

---

## 🏗️ Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     END USERS (Global)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────────┐    ┌────────▼────────────────┐
│   Cloudflare Pages   │    │  Cloudflare Workers     │
│  (Frontend/Static)   │    │  (Edge Functions)       │
│                      │    │  (Rate Limiting, Auth)  │
└───────┬──────────────┘    └────────┬────────────────┘
        │                            │
        └──────────────┬─────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Cloudflare Gateway/Proxy   │
        │  - WAF Rules                │
        │  - DDoS Protection          │
        │  - Rate Limiting            │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────────┐
        │   Railway Backend (Python)      │
        │   - FastAPI Application         │
        │   - Auto-scaling                │
        │   - Health checks               │
        └──────────────┬──────────────────┘
                       │
        ┌──────────────┴────────────────────┐
        │                                   │
    ┌───▼────┐                    ┌────────▼────┐
    │ D1/SQL │                    │  R2 Storage │
    │Database│                    │(words.txt,  │
    │        │                    │ backups)    │
    └────────┘                    └─────────────┘
```

---

## 📊 Infrastructure Components

### **1. Frontend (Cloudflare Pages)**
- **Purpose**: Serve Angular application globally
- **Features**: 
  - Automatic deployments from GitHub
  - Unlimited requests
  - Built-in serverless functions
  - Cache control and purging
  - SSL/TLS auto-renewal
- **Cost**: FREE (first 10 builds/month free, then $0.20/build)

### **2. Backend (Railway/Fly.io)**
- **Purpose**: Run FastAPI application
- **Features**:
  - Auto-scaling
  - Health monitoring
  - Environment variable management
  - Automatic rollbacks
  - PostgreSQL included
- **Cost**: ~$5-25/month depending on usage

### **3. Cloudflare Workers (Optional but Recommended)**
- **Purpose**: Edge functions for:
  - Authentication
  - Request validation
  - Response transformation
  - Rate limiting
  - Analytics
- **Cost**: FREE for first 100K requests/day

### **4. Cloudflare R2**
- **Purpose**: Object storage for static files
- **Features**:
  - No egress charges
  - Fully S3-compatible API
  - Integrated with Workers and Pages
- **Cost**: $0.015/GB storage, FREE egress

### **5. Cloudflare D1**
- **Purpose**: SQL database
- **Features**:
  - SQLite at the edge
  - Auto-scaling
  - Automatic backups
- **Cost**: FREE tier available

---

## 🎯 Step-by-Step Migration Process

### **Phase 1: Preparation (1-2 hours)**

#### 1.1 Create Cloudflare Account
```bash
# Visit https://dash.cloudflare.com/sign-up
# Create free account or upgrade to Pro/Business
```

#### 1.2 Setup Railway Account
```bash
# Visit https://railway.app
# Sign up with GitHub
# Create new project
```

#### 1.3 Domain Setup
```bash
# Update domain nameservers to Cloudflare:
# ns1.cloudflare.com
# ns2.cloudflare.com
# ns3.cloudflare.com
# ns4.cloudflare.com

# Wait 24-48 hours for propagation
```

---

### **Phase 2: Frontend Deployment (30 minutes)**

#### 2.1 Update Angular Production Build
**File**: `frontend/angular.json`

Configure for Cloudflare Pages:
```json
{
  "projects": {
    "word-filter-frontend": {
      "architect": {
        "build": {
          "configurations": {
            "production": {
              "outputHashing": "all",
              "optimization": true,
              "buildOptimizer": true,
              "sourceMap": false,
              "namedChunks": false,
              "aot": true,
              "extractLicenses": true,
              "vendorChunk": false
            }
          }
        }
      }
    }
  }
}
```

#### 2.2 Create Cloudflare Pages Configuration
**File**: `wrangler.toml` (root directory)

```toml
name = "word-filter-app"
type = "javascript"
main = "src/index.js"

[env.production]
name = "word-filter-app-prod"
routes = [
  { pattern = "example.com", zone_name = "example.com" }
]
```

#### 2.3 Environment Configuration
**File**: `frontend/src/environments/environment.prod.ts`

```typescript
export const environment = {
  production: true,
  // Use relative API paths - Cloudflare will route to backend
  apiUrl: '/api',
  // Or use your domain: 'https://api.example.com'
  baseUrl: 'https://example.com'
};
```

#### 2.4 Connect to GitHub
```bash
# In Cloudflare dashboard:
# 1. Pages > Create project > Connect to Git
# 2. Select word-filter-app repository
# 3. Build settings:
#    - Framework preset: Angular
#    - Build command: npm run build
#    - Build output directory: dist/word-filter-frontend
# 4. Set environment variables
# 5. Deploy
```

---

### **Phase 3: Backend Deployment (45 minutes)**

#### 3.1 Prepare Backend for Railway

**File**: `backend/.railway/Procfile`
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**File**: `backend/Dockerfile.railway`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT}/health')"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
```

**File**: `backend/requirements.txt` (Updated)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
beautifulsoup4==4.12.2
requests==2.31.0
aiohttp==3.9.1
lxml==4.9.3
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
# Cloudflare integration (optional)
wrangler==3.0.0
# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
# Performance
redis==5.0.1
# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

#### 3.2 Create Health Check Endpoint
**File**: `backend/main.py` (Add to FastAPI app)

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.2.0"
    }

@app.get("/metrics/ready")
async def readiness_check():
    """Kubernetes/Railway readiness probe"""
    try:
        # Check if word database is accessible
        await get_word_count()
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False}, 503
```

#### 3.3 Deploy to Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# In project directory
cd backend

# Initialize Railway
railway init

# Add environment variables
railway variable set ENVIRONMENT=production
railway variable set LOG_LEVEL=INFO
railway variable set CORS_ORIGINS=https://example.com,https://www.example.com
railway variable set DATABASE_URL=postgresql://...
railway variable set REDIS_URL=redis://...

# Deploy
railway up
```

---

### **Phase 4: Cloudflare Workers Setup (30 minutes)**

#### 4.1 Create Worker for API Gateway
**File**: `workers/api-gateway.ts`

```typescript
import { Router, RequestError } from 'itty-router'

const router = Router()

// Rate limiting
const rateLimitMap = new Map()

function checkRateLimit(ip: string): boolean {
  const now = Date.now()
  const limit = rateLimitMap.get(ip) || { count: 0, reset: now + 60000 }
  
  if (now > limit.reset) {
    rateLimitMap.set(ip, { count: 1, reset: now + 60000 })
    return true
  }
  
  if (limit.count > 100) {
    return false
  }
  
  limit.count++
  return true
}

// Health check
router.get('/health', () => {
  return new Response(JSON.stringify({ status: 'ok' }), {
    headers: { 'content-type': 'application/json' }
  })
})

// API proxy with rate limiting
router.all('/api/*', async (request, env) => {
  const clientIp = request.headers.get('cf-connecting-ip') || '0.0.0.0'
  
  if (!checkRateLimit(clientIp)) {
    return new Response('Too many requests', { status: 429 })
  }
  
  const url = new URL(request.url)
  const backendUrl = env.BACKEND_URL + url.pathname + url.search
  
  try {
    const response = await fetch(backendUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    })
    
    // Add security headers
    const newResponse = new Response(response.body, response)
    newResponse.headers.set('X-Content-Type-Options', 'nosniff')
    newResponse.headers.set('X-Frame-Options', 'SAMEORIGIN')
    newResponse.headers.set('X-XSS-Protection', '1; mode=block')
    newResponse.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    return newResponse
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Backend unavailable' }), {
      status: 502,
      headers: { 'content-type': 'application/json' }
    })
  }
})

// 404 handler
router.all('*', () => {
  return new Response('Not found', { status: 404 })
})

export default {
  fetch: router.handle
}
```

#### 4.2 Deploy Worker
```bash
# Install Wrangler
npm install -D wrangler

# Create wrangler.toml
cat > wrangler.toml << EOF
name = "word-filter-api-gateway"
type = "javascript"
account_id = "YOUR_ACCOUNT_ID"
workers_dev = true

[env.production]
name = "word-filter-api-gateway-prod"
routes = [
  { pattern = "api.example.com/*", zone_name = "example.com" }
]

[env.production.vars]
BACKEND_URL = "https://backend-railway-url.railway.app"
EOF

# Deploy
wrangler deploy
```

---

### **Phase 5: CI/CD Pipeline Setup (45 minutes)**

#### 5.1 GitHub Actions for Frontend
**File**: `.github/workflows/deploy-frontend.yml`

```yaml
name: Deploy Frontend to Cloudflare Pages

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy-frontend.yml'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'

env:
  NODE_VERSION: '20.x'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Lint
        working-directory: frontend
        run: npm run lint --if-present

      - name: Run tests
        working-directory: frontend
        run: npm run test:ci --if-present

      - name: Build production
        working-directory: frontend
        env:
          NG_BUILD_OPTIMIZATION: true
        run: npm run build -- --configuration production

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: word-filter-app
          directory: frontend/dist/word-filter-frontend
          branch: ${{ github.head_ref || github.ref_name }}
```

#### 5.2 GitHub Actions for Backend
**File**: `.github/workflows/deploy-backend.yml`

```yaml
name: Deploy Backend to Railway

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
      - '.github/workflows/deploy-backend.yml'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'

env:
  PYTHON_VERSION: '3.11'

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: word_filter_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        working-directory: backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Lint with pylint
        working-directory: backend
        run: pylint *.py --disable=C0111,C0103 || true

      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/word_filter_test
        run: |
          python -m pytest tests/ -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to Railway
        uses: railway-app/railway-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
          service: word-filter-backend
          workingDirectory: backend
```

---

### **Phase 6: Database Migration (1 hour)**

#### 6.1 PostgreSQL Setup on Railway

```bash
# In Railway dashboard:
# 1. Create new PostgreSQL database
# 2. Get connection string
# 3. Add to environment: DATABASE_URL

# Local migration test
cd backend
export DATABASE_URL=postgresql://user:password@host:5432/word_filter
python migrate_db.py
```

#### 6.2 Create Migration Script
**File**: `backend/migrate_db.py`

```python
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Create tables
with engine.connect() as connection:
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            word VARCHAR(255) UNIQUE NOT NULL,
            length INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_word_length (length),
            INDEX idx_word (word(10))
        )
    """))
    
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS api_stats (
            id SERIAL PRIMARY KEY,
            endpoint VARCHAR(255),
            method VARCHAR(10),
            status_code INT,
            response_time_ms FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_timestamp (timestamp)
        )
    """))
    
    connection.commit()
    print("✅ Database migration complete")
```

---

### **Phase 7: DNS & SSL Configuration (30 minutes)**

#### 7.1 Cloudflare DNS Records

```
Type  | Name              | Content                  | TTL
------|-------------------|--------------------------|------
A     | @                 | 104.21.x.x (CF)         | Auto
CNAME | www               | example.com              | Auto
CNAME | api               | backend-railway-url      | Auto
MX    | @                 | mail.example.com (if)    | Auto
TXT   | @                 | v=spf1 (if email)        | Auto
```

#### 7.2 SSL/TLS Settings

```
Cloudflare Dashboard > SSL/TLS:
- Mode: Full (strict) - recommended
- Certificate: Let's Encrypt (auto-renewed)
- Minimum TLS Version: 1.2
- Opportunistic Encryption: ON
- Always Use HTTPS: ON
```

---

### **Phase 8: Optimization & Security (1 hour)**

#### 8.1 Caching Strategy
**File**: `frontend/_headers` (Cloudflare Pages)

```
# HTML - no cache
/index.html
  Cache-Control: no-cache, no-store, must-revalidate
  
# JS/CSS - 1 year cache (versioned)
/*.bundle.js
  Cache-Control: public, max-age=31536000, immutable

/styles.*.css
  Cache-Control: public, max-age=31536000, immutable

# API - no cache
/api/*
  Cache-Control: no-cache

# Images - 1 month
/assets/images/*
  Cache-Control: public, max-age=2592000
```

#### 8.2 WAF Rules
**File**: `cloudflare-waf-rules.json`

```json
{
  "rules": [
    {
      "name": "Rate Limit - API Requests",
      "expression": "(http.host eq \"api.example.com\")",
      "action": "challenge",
      "threshold": "100",
      "period": 60
    },
    {
      "name": "Block SQL Injection",
      "expression": "(http.request.uri.query contains \"union\" or http.request.uri.query contains \"select\")",
      "action": "block"
    },
    {
      "name": "Geo-block if needed",
      "expression": "(cf.country in {\"CN\" \"RU\"})",
      "action": "block"
    }
  ]
}
```

---

## 🔄 Migration Checklist

- [ ] Create Cloudflare account
- [ ] Create Railway account  
- [ ] Update domain nameservers to Cloudflare
- [ ] Build and deploy frontend to Pages
- [ ] Deploy backend to Railway
- [ ] Create and deploy Workers
- [ ] Setup CI/CD pipelines
- [ ] Migrate database
- [ ] Configure DNS records
- [ ] Setup SSL/TLS
- [ ] Configure WAF rules
- [ ] Setup monitoring & alerts
- [ ] Run load testing
- [ ] Execute switchover
- [ ] Monitor for 24 hours
- [ ] Remove CIVO resources
- [ ] Archive old deployment configs

---

## 📊 Cost Analysis

| Component | Old (CIVO) | New (Cloudflare) | Savings |
|-----------|-----------|------------------|---------|
| Kubernetes | $25-50/mo | FREE | -$50 |
| Pages/CDN | N/A | FREE | - |
| Workers | N/A | FREE (100K req) | - |
| Backend | Included | $5-20/mo | -$10 |
| Database | Included | $0-10/mo | -$10 |
| Storage (R2) | $20/mo | $0.015/GB | -$15 |
| **TOTAL** | **$45-80/mo** | **$5-30/mo** | **$15-75** |

---

## 🚀 Performance Metrics Expected

| Metric | CIVO | Cloudflare |
|--------|------|-----------|
| Global Latency | 150-300ms | <50ms |
| Time to First Byte | 200-400ms | 50-100ms |
| Largest Contentful Paint | 2-3s | 0.5-1s |
| Cache Hit Ratio | 40-60% | 80-95% |
| Uptime SLA | 99.5% | 99.97% |
| DDoS Protection | Limited | Enterprise |

---

## 🆘 Troubleshooting

### **Frontend not loading**
```bash
# Check build output
wrangler pages project list
wrangler pages deployment list

# Clear Cloudflare cache
curl -X POST https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"purge_everything":true}'
```

### **Backend connection issues**
```bash
# Test Railway deployment
railway logs

# Check Railway health
railway status

# Test locally
curl http://backend-railway-url/health
```

### **DNS propagation issues**
```bash
# Check DNS records
nslookup example.com
dig example.com

# Wait for propagation (up to 48 hours)
```

---

## 📞 Support & Resources

- **Cloudflare Docs**: https://developers.cloudflare.com
- **Railway Docs**: https://docs.railway.app
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Community**: Cloudflare Community Forums, Railway Discord

---

**Next Steps**: Follow Phase 1 to begin the migration! 🎯
