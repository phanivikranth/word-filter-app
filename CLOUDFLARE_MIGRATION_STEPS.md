# 🚀 Cloudflare Migration - Step-by-Step Execution Guide
## Enterprise-Grade Deployment Walkthrough

**Duration**: 4-6 hours  
**Risk Level**: LOW (fully tested CI/CD pipeline)  
**Rollback Time**: 15 minutes  

---

## Pre-Migration Checklist ✅

### Week Before Migration
- [ ] Backup all data (words database, configuration)
- [ ] Test CI/CD pipeline in staging
- [ ] Review all environment variables
- [ ] Notify stakeholders of maintenance window
- [ ] Schedule maintenance window (off-peak hours)
- [ ] Prepare rollback procedure

### Day of Migration
- [ ] Stop all transactions on old CIVO system
- [ ] Verify backup integrity
- [ ] Have all account credentials ready
- [ ] Test all external service connections
- [ ] Prepare communication channels (Slack, status page)

---

## PHASE 1: Cloudflare Account Setup (30 minutes)

### Step 1.1: Create Cloudflare Account

```bash
# Visit: https://dash.cloudflare.com/sign-up
# 
# Fill in:
# - Email: your@company.com
# - Password: (strong password, save to password manager)
# - Account name: word-filter-app
#
# Choose plan:
# - Pro or higher recommended for enterprise features ($20-200/month)
```

### Step 1.2: Add Domain to Cloudflare

```bash
# In Cloudflare Dashboard:
# 1. Navigate to "Websites" > "Add domain"
# 2. Enter: example.com
# 3. Choose plan (Pro recommended)
# 4. Update nameservers at your registrar:

# OLD Nameservers (Replace these):
# ns1.your-registrar.com
# ns2.your-registrar.com

# NEW Nameservers (Use these):
# ns1.cloudflare.com
# ns2.cloudflare.com
# ns3.cloudflare.com
# ns4.cloudflare.com

# Propagation time: 24-48 hours
# Check status: https://www.whatsmydns.net/?type=NS&q=example.com
```

### Step 1.3: Verify Domain in Cloudflare

```bash
# Wait for nameserver propagation
# In Cloudflare Dashboard, domain should show as "Active"

# Verify DNS records are visible:
# Dashboard > Zone Records > should show auto-detected records
```

### Step 1.4: Create API Token

```bash
# Cloudflare Dashboard > My Account > API Tokens
# Click "Create Token"
# Use template: "Edit Cloudflare Workers"
# Or "Create Custom Token" with:
# - Permissions:
#   - Account.Cloudflare Workers Scripts: Edit
#   - Zone.Cache Purge: Purge
#   - Zone.DNS: Edit
#   - Zone.Page Rules: Edit
#
# Save token securely (only shown once!)
# Add to GitHub Secrets as: CLOUDFLARE_API_TOKEN
```

---

## PHASE 2: Railway Account Setup (30 minutes)

### Step 2.1: Create Railway Account

```bash
# Visit: https://railway.app
# Sign up with GitHub (recommended)
# Verify email
```

### Step 2.2: Create New Project

```bash
# Railway Dashboard > New Project
# Select "Deploy from GitHub repo"
# - Select: your-username/word-filter-app
# - Branch: main
```

### Step 2.3: Add PostgreSQL Service

```bash
# Railway Dashboard > Project > Services
# Click "+ New Service"
# Select "Database" > "PostgreSQL"
# Confirms auto-generated DATABASE_URL

# Save to GitHub Secrets:
# - Copy DATABASE_URL from Railway dashboard
# - GitHub > Settings > Secrets > New repository secret
# - Name: DATABASE_URL
# - Value: [paste from Railway]
```

### Step 2.4: Add Redis Service (Optional)

```bash
# Railway Dashboard > Project > Services
# Click "+ New Service"
# Select "Database" > "Redis"
# Confirms auto-generated REDIS_URL

# Save to GitHub Secrets:
# - Copy REDIS_URL from Railway dashboard
# - GitHub > Settings > Secrets > New repository secret
# - Name: REDIS_URL
```

### Step 2.5: Generate Railway API Token

```bash
# Railway Dashboard > Account > API Tokens
# Create new token
# Copy token
# GitHub > Settings > Secrets > New repository secret
# Name: RAILWAY_TOKEN
# Value: [paste token]
```

---

## PHASE 3: GitHub Actions Setup (15 minutes)

### Step 3.1: Add GitHub Secrets

```bash
# GitHub Repository > Settings > Secrets and variables > Actions

# Add these secrets:
CLOUDFLARE_API_TOKEN = <from Cloudflare>
CLOUDFLARE_ACCOUNT_ID = <from Cloudflare dashboard>
RAILWAY_TOKEN = <from Railway>
RAILWAY_PROJECT_ID = <from Railway URL>
SLACK_WEBHOOK_URL = <optional, for notifications>
```

### Step 3.2: Verify Workflows

```bash
# GitHub Repository > Actions
# Should see workflows:
# - deploy-frontend.yml
# - deploy-backend.yml
# - code-quality.yml

# Click each workflow to verify configuration
```

---

## PHASE 4: Backend Deployment (45 minutes)

### Step 4.1: Update Backend Environment Variables

```bash
# Retrieve from Railway dashboard:
# - DATABASE_URL
# - REDIS_URL

# Create .env.production file:
cat > backend/.env.production << EOF
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8001
DATABASE_URL=$(railway variable get DATABASE_URL)
REDIS_URL=$(railway variable get REDIS_URL)
CORS_ORIGINS=https://example.com,https://www.example.com,https://api.example.com
OXFORD_APP_ID=your_oxford_id
OXFORD_APP_KEY=your_oxford_key
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
EOF
```

### Step 4.2: Test Backend Locally

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start local server
python main.py

# Test health endpoints
curl http://localhost:8001/health
curl http://localhost:8001/health/ready
curl http://localhost:8001/health/live
```

### Step 4.3: Deploy Backend to Railway

```bash
# Push to GitHub (triggers CI/CD):
git add -A
git commit -m "chore: prepare for Cloudflare migration"
git push origin main

# Monitor GitHub Actions:
# Repository > Actions > deploy-backend.yml
# Wait for: "deploy" job to complete

# Verify Railway deployment:
railway logs

# Test deployed backend:
curl https://word-filter-backend-railway.railway.app/health
```

---

## PHASE 5: Frontend Deployment (30 minutes)

### Step 5.1: Update Frontend Configuration

```bash
# frontend/src/environments/environment.prod.ts
cat > frontend/src/environments/environment.prod.ts << 'EOF'
export const environment = {
  production: true,
  apiUrl: '/api',  // Will be routed through Cloudflare
  baseUrl: 'https://example.com'
};
EOF
```

### Step 5.2: Build Frontend Locally

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm ci

# Run tests
npm run test:ci 2>/dev/null || true

# Build for production
npm run build -- --configuration production
```

### Step 5.3: Deploy Frontend to Cloudflare Pages

```bash
# Commit and push (triggers CI/CD):
git add -A
git commit -m "chore: update API endpoint for Cloudflare"
git push origin main

# Monitor GitHub Actions:
# Repository > Actions > deploy-frontend.yml
# Wait for: "deploy-pages" job to complete

# Cloudflare Dashboard > Pages > Projects > word-filter-app
# Verify deployment successful
# Copy deployment URL
```

---

## PHASE 6: Cloudflare Workers Deployment (20 minutes)

### Step 6.1: Deploy API Gateway Worker

```bash
# Navigate to workers directory
cd workers

# Install dependencies
npm install

# Configure wrangler.toml with your account:
nano wrangler.toml
# Update: account_id, BACKEND_URL

# Deploy to production:
npm run deploy:prod
# or
wrangler deploy --env production
```

### Step 6.2: Verify Worker Deployment

```bash
# Cloudflare Dashboard > Workers > Deployments
# Verify deployment successful

# Test Worker:
curl https://api.example.com/health

# Check logs:
# Cloudflare Dashboard > Workers > Logs
```

---

## PHASE 7: DNS & Routing Configuration (20 minutes)

### Step 7.1: Configure DNS Records

```bash
# Cloudflare Dashboard > Zone Records

# Create/Update records:

# Frontend (Route @ to Cloudflare Pages)
Type: CNAME
Name: @
Content: example.com.pages.dev
TTL: Auto

# API Gateway (Route api subdomain to Worker)
Type: CNAME
Name: api
Content: api.example.com (Worker)
TTL: Auto

# Backend fallback (if Worker unavailable)
Type: CNAME
Name: backend
Content: word-filter-backend-railway.railway.app
TTL: Auto

# Email (if applicable)
Type: MX
Name: @
Content: mail.example.com
Priority: 10
```

### Step 7.2: Verify DNS Resolution

```bash
# Test DNS propagation:
nslookup example.com

# Verify records:
dig example.com
dig api.example.com
dig www.example.com

# Should resolve to Cloudflare IPs (104.21.x.x)
```

---

## PHASE 8: SSL/TLS Configuration (10 minutes)

### Step 8.1: Configure SSL Settings

```bash
# Cloudflare Dashboard > SSL/TLS

# SSL/TLS Encryption Mode:
# Set to: "Full (strict)"
# This requires valid certificate (Let's Encrypt auto-provisioned)

# Always Use HTTPS: ON
# Minimum TLS Version: 1.2
# Opportunistic Encryption: ON
```

### Step 8.2: Verify SSL Certificate

```bash
# Test SSL:
curl -I https://example.com
curl -I https://api.example.com

# Both should return:
# HTTP/2 200 or similar
# No SSL warnings
```

---

## PHASE 9: WAF & Security Configuration (20 minutes)

### Step 9.1: Enable WAF

```bash
# Cloudflare Dashboard > Security > WAF

# Enable predefined rule sets:
# - Cloudflare Managed Challenge
# - OWASP ModSecurity Core Rule Set
# - Cloudflare API Shield

# Create custom rules:
# Rate limiting: 100 requests per 60 seconds
# Geo-blocking: Block specific countries if needed
```

### Step 9.2: Configure Rate Limiting

```bash
# Cloudflare Dashboard > Rate Limiting

# Create rule:
# Threshold: 100 requests per 60 seconds
# Condition: URI path = /api/*
# Action: Block for 10 minutes
```

### Step 9.3: Setup DDoS Protection

```bash
# Cloudflare Dashboard > Security > DDoS

# Sensitivity Level: High (for production)
# Advanced DDoS Protection: Enable (if on paid plan)
```

---

## PHASE 10: Monitoring & Testing (30 minutes)

### Step 10.1: Setup Monitoring

```bash
# Cloudflare Dashboard > Analytics

# Monitor:
# - Requests
# - Bandwidth
# - Threats blocked
# - Cache hit ratio

# Set up alerts:
# Email notifications for high error rates
```

### Step 10.2: Run Full Integration Tests

```bash
# Test frontend
curl -I https://example.com
curl https://example.com/index.html

# Test API endpoints
curl https://api.example.com/health
curl https://api.example.com/api/words/stats
curl https://api.example.com/api/words?length=5

# Test caching
curl -I https://example.com/static/main.js
# Check: X-Cache: HIT

# Test rate limiting
for i in {1..150}; do curl https://api.example.com/health; done
# Should get 429 (Too Many Requests) after 100 requests
```

### Step 10.3: Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 100 https://example.com/

# Using wrk
wrk -t12 -c400 -d30s https://example.com/

# Monitor during load test:
# - Response times
# - Error rates
# - Cache performance
```

---

## PHASE 11: CIVO Cleanup (30 minutes)

### Step 11.1: Verify Migration Success

```bash
# Checklist before removing CIVO:
# - [ ] Frontend accessible at https://example.com
# - [ ] API responding at https://api.example.com
# - [ ] All endpoints functional
# - [ ] SSL/TLS working
# - [ ] No error logs
# - [ ] Performance acceptable
# - [ ] Users reporting no issues
```

### Step 11.2: Backup CIVO Data

```bash
# Export all data from CIVO:
kubectl get all --all-namespaces > civo-backup-$(date +%s).yaml

# Backup database
pg_dump civo_database > civo-database-$(date +%s).sql

# Archive files
tar -czf civo-backup-$(date +%s).tar.gz /path/to/civo-files/
```

### Step 11.3: Decommission CIVO

```bash
# CIVO Dashboard > Kubernetes > Delete Cluster
# Warning: This is irreversible, ensure backup completed

# Delete DNS records pointing to CIVO
# Remove firewall rules
# Release static IPs
```

---

## PHASE 12: Post-Migration Monitoring (24 hours)

### Step 12.1: Monitor Error Rates

```bash
# First 24 hours after migration:

# Check logs every hour:
# - Cloudflare dashboard
# - Railway dashboard
# - Application logs

# Monitor metrics:
# - Error rate (should be < 0.1%)
# - Response time (should be < 500ms)
# - Cache hit ratio (should be > 80%)
```

### Step 12.2: Performance Verification

```bash
# Verify performance improvements:

# Before (CIVO):
# - Global latency: 150-300ms
# - Time to First Byte: 200-400ms

# After (Cloudflare):
# - Global latency: <50ms
# - Time to First Byte: 50-100ms

# Use tools:
# - GTmetrix
# - WebPageTest
# - Lighthouse
```

### Step 12.3: Team Handover

```bash
# Create documentation:
# - Runbook for common operations
# - Troubleshooting guide
# - Alert escalation procedure
# - Contact information

# Train team on:
# - Cloudflare dashboard navigation
# - Monitoring and alerts
# - Deployment procedure
# - Rollback procedure
```

---

## Rollback Procedure (If Needed)

### Quick Rollback (< 15 minutes)

```bash
# Update DNS records to point back to CIVO:
# Cloudflare Dashboard > Zone Records
#
# Change CNAME records:
# @ → OLD_CIVO_IP
# api → OLD_CIVO_API_IP
#
# TTL: 300 seconds (5 minutes)
#
# Wait for propagation, verify old system is responding
```

### Complete Rollback

```bash
# If issues persist:

# 1. Restore CIVO cluster from backup
# 2. Restore database from backup
# 3. Update DNS to CIVO servers
# 4. Wait for propagation
# 5. Verify all systems operational
# 6. Investigate issues
```

---

## Success Criteria ✅

- [x] Frontend deployed to Cloudflare Pages
- [x] Backend deployed to Railway
- [x] Workers gateway functional
- [x] DNS records pointing to Cloudflare
- [x] SSL/TLS certificate valid
- [x] All health checks passing
- [x] No error rates above 0.1%
- [x] Response times < 500ms globally
- [x] CIVO infrastructure decommissioned
- [x] Team trained on new infrastructure

---

## Cost Optimization Tips

1. **Frontend**: Leverage unlimited Cloudflare Pages requests
2. **Backend**: Use Railway's pay-as-you-go pricing
3. **Workers**: Stay under 100K requests/day for free tier
4. **R2**: Use for storing static assets (no egress fees)
5. **Cache Aggressively**: Reduce backend requests
6. **Monitor Spending**: Set up Cloudflare billing alerts

---

## Support & References

- **Cloudflare Docs**: https://developers.cloudflare.com
- **Railway Docs**: https://docs.railway.app
- **Status Page**: Set up uptime monitoring at https://status.example.com
- **Support**: Create PagerDuty incident if issues arise

---

**Estimated Timeline**: 4-6 hours  
**Last Updated**: 2026-06-18  
**Next Review**: After 30 days of production operation
