# Environment Variables Configuration Guide
# Enterprise-Level Cloudflare Migration

## Overview
This document outlines all environment variables needed for the complete Cloudflare migration.

---

## Frontend Environment Variables

### `.env.production` (Cloudflare Pages)

```env
# Application
ENVIRONMENT=production
APP_NAME=Word Filter App
VERSION=2.2.0
DEBUG=false

# API Configuration
NG_API_URL=https://api.example.com
NG_BACKEND_API_URL=https://api.example.com/api
NG_TIMEOUT=30000

# Cloudflare Configuration
NG_CLOUDFLARE_ENABLED=true
NG_CLOUDFLARE_ZONE_ID=your_zone_id
NG_CLOUDFLARE_ANALYTICS=true

# Security
NG_CSP_ENABLED=true
NG_SECURITY_HEADERS=true
NG_CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com

# Feature Flags
NG_FEATURE_OXFORD_API=true
NG_FEATURE_SYNONYMS=true
NG_FEATURE_ANALYTICS=true
```

### `frontend/src/environments/environment.prod.ts`

```typescript
export const environment = {
  production: true,
  apiUrl: '/api',
  baseUrl: 'https://example.com',
  apiTimeout: 30000,
  features: {
    oxfordApi: true,
    synonyms: true,
    analytics: true
  },
  cloudflare: {
    enabled: true,
    analyticsEnabled: true
  }
};
```

---

## Backend Environment Variables

### Production (Railway)

```env
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
PORT=8001
HOST=0.0.0.0

# FastAPI
WORKERS=4
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000
WORKER_TIMEOUT=30

# CORS Configuration
CORS_ORIGINS=https://example.com,https://www.example.com,https://api.example.com
CORS_CREDENTIALS=true
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_HEADERS=Content-Type,Authorization,X-Requested-With

# Database (Railway PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/word_filter_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_RECYCLE=3600
DATABASE_ECHO=false

# Redis (for caching and sessions)
REDIS_URL=redis://user:password@host:6379/0
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_RETRY_ON_TIMEOUT=true
CACHE_TTL=3600

# Storage (Cloudflare R2)
R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
R2_BUCKET_NAME=word-filter-prod
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_REGION=auto

# Oxford API Integration
OXFORD_APP_ID=your_oxford_app_id
OXFORD_APP_KEY=your_oxford_app_key
OXFORD_API_ENABLED=true
OXFORD_API_TIMEOUT=10

# Monitoring & Logging
SENTRY_DSN=https://your-sentry-dsn
DATADOG_API_KEY=your_datadog_key
DATADOG_ENABLED=true

# Security
SECRET_KEY=your-super-secret-key-min-32-chars
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Cloudflare Integration
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ZONE_ID=your_zone_id
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_CACHE_PURGE=true

# Feature Flags
FEATURE_OXFORD_API=true
FEATURE_SYNONYMS=true
FEATURE_ADVANCED_FILTERING=true
FEATURE_ANALYTICS=true
```

### `backend/.env.example`

```env
# Development/Testing environment file
# Copy to .env and fill in your values

# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true
PORT=8001
HOST=127.0.0.1

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/word_filter_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:4200,http://localhost:8001

# API Keys (leave empty for development)
OXFORD_APP_ID=
OXFORD_APP_KEY=

# Security (use weak keys for development)
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET=dev-jwt-secret-change-in-production
```

---

## Cloudflare Configuration

### Cloudflare Pages Environment Variables

Set in Cloudflare Dashboard > Pages > Settings > Environment Variables

```
BACKEND_URL = https://api.example.com
ENVIRONMENT = production
ANALYTICS_ENABLED = true
CACHE_BUSTER = {random_id}
```

### Cloudflare Workers Environment Variables

Set in `wrangler.toml`:

```toml
[env.production.vars]
BACKEND_URL = "https://word-filter-backend-railway.railway.app"
ENVIRONMENT = "production"
API_VERSION = "2.2.0"
LOG_LEVEL = "info"

[[kv_namespaces]]
binding = "CACHE"
id = "your_namespace_id"
```

### Cloudflare DNS Records

```
Type  | Name  | Content                         | TTL
------|-------|----------------------------------|-----
A     | @     | 104.21.x.x (Cloudflare IP)     | Auto
CNAME | www   | example.com                     | Auto
CNAME | api   | backend-railway.railway.app     | Auto
CNAME | cdn   | example.com                     | Auto
TXT   | @     | v=spf1 include:_spf.example.com | Auto
MX    | @     | mail.example.com (priority 10)  | Auto
```

---

## Railway Configuration

### Project Environment Variables

Set in Railway Dashboard > Project > Services > Environment

1. **Backend Service Environment Variables**

```
DATABASE_URL: postgresql://user:password@host:5432/word_filter_prod
REDIS_URL: redis://user:password@host:6379/0
ENVIRONMENT: production
LOG_LEVEL: INFO
PORT: 8001
CORS_ORIGINS: https://example.com,https://www.example.com
```

2. **Add PostgreSQL Service**
   - Add PostgreSQL from Railway templates
   - Auto-generates DATABASE_URL

3. **Add Redis Service** (optional)
   - Add Redis from Railway templates
   - Auto-generates REDIS_URL

---

## GitHub Actions Secrets

Set in GitHub > Settings > Secrets and Variables > Actions

```
CLOUDFLARE_API_TOKEN = your_api_token
CLOUDFLARE_ACCOUNT_ID = your_account_id
RAILWAY_TOKEN = your_railway_api_token
RAILWAY_PROJECT_ID = your_project_id
SLACK_WEBHOOK_URL = https://hooks.slack.com/services/...
SONAR_TOKEN = your_sonarcloud_token
```

---

## Local Development Setup

### Create `.env.local`

```bash
# Backend
cd backend
cat > .env.local << EOF
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true
PORT=8001
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/word_filter_dev
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:4200,http://localhost:8001
OXFORD_APP_ID=your_dev_id
OXFORD_APP_KEY=your_dev_key
SECRET_KEY=dev-key-only-for-testing
EOF
```

### Create `frontend/.env.local`

```bash
cd frontend
cat > .env.local << EOF
NG_API_URL=http://localhost:8001
NG_ENVIRONMENT=development
EOF
```

---

## Environment Setup Commands

### 1. Setup Production Environment

```bash
# Using Railway CLI
railway link word-filter-prod

# Set environment variables
railway variable set ENVIRONMENT=production
railway variable set LOG_LEVEL=INFO
railway variable set DATABASE_URL=postgresql://...
railway variable set REDIS_URL=redis://...
railway variable set CORS_ORIGINS=https://example.com,https://www.example.com
```

### 2. Setup Cloudflare

```bash
# Using Wrangler CLI
wrangler login

# Configure wrangler.toml with your account_id
# Then set variables in wrangler.toml or Cloudflare dashboard
```

### 3. Update Frontend Configuration

```bash
# Update Angular environments/environment.prod.ts
# Update environment.apiUrl to point to Cloudflare API endpoint
```

---

## Validation Checklist

- [ ] All required environment variables are set
- [ ] Database credentials are correct
- [ ] API keys are valid and have proper permissions
- [ ] CORS origins are correctly configured
- [ ] Redis connection is working
- [ ] Cloudflare API token has necessary permissions
- [ ] Railway services are linked and configured
- [ ] GitHub Secrets are set for CI/CD
- [ ] SSL/TLS certificates are valid
- [ ] Health check endpoints return 200

---

## Security Best Practices

1. **Never commit .env files** - Add to .gitignore
2. **Use strong secrets** - Minimum 32 characters for SECRET_KEY
3. **Rotate keys regularly** - Update keys quarterly
4. **Limit permissions** - Use least privilege principle
5. **Use separate environments** - Dev, staging, production
6. **Monitor access logs** - Check for unauthorized access
7. **Enable 2FA** - On all provider accounts (GitHub, Cloudflare, Railway)
8. **Audit environment variables** - Review quarterly
9. **Use managed secrets** - Avoid hardcoding in code
10. **Document sensitive info** - Keep in secure location

---

## Troubleshooting

### Backend not connecting to database
```bash
# Check DATABASE_URL format
# Test connection: psql $DATABASE_URL -c "SELECT 1"
# Verify firewall rules in Railway
```

### API calls failing with CORS error
```bash
# Check CORS_ORIGINS environment variable
# Verify it includes frontend domain
# Clear browser cache and try again
```

### Cloudflare caching issues
```bash
# Purge cache: wrangler publish
# Check cache headers in _headers file
# Verify page rules in Cloudflare dashboard
```

---

**Last Updated**: 2026-06-18  
**Maintained By**: DevOps Team
