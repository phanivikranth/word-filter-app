# 🚀 Quick Deployment Guide

## Deploy in 3 Steps

### Step 1: Prerequisites
Ensure you have Docker and Docker Compose installed:
```bash
docker --version
docker compose version
```

### Step 2: Configure
```bash
# Copy environment template (already done if .env exists)
cp .env.example .env

# Edit .env if needed (optional for local deployment)
```

### Step 3: Deploy

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh up
```

**Windows PowerShell:**
```powershell
.\deploy.ps1 up
```

## Access Your Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Common Commands

| Action | Linux/Mac | Windows |
|--------|-----------|---------|
| Start | `./deploy.sh up` | `.\deploy.ps1 up` |
| Stop | `./deploy.sh down` | `.\deploy.ps1 down` |
| Restart | `./deploy.sh restart` | `.\deploy.ps1 restart` |
| View Logs | `./deploy.sh logs` | `.\deploy.ps1 logs` |
| Rebuild | `./deploy.sh rebuild` | `.\deploy.ps1 rebuild` |

## What's Included

✅ **Production-ready Docker setup**
- Multi-stage builds for optimized images
- Health checks for both services
- Automatic restart policies
- Volume management for logs

✅ **Deployment scripts**
- `deploy.sh` for Linux/Mac
- `deploy.ps1` for Windows PowerShell
- Automatic environment setup

✅ **Documentation**
- `DEPLOYMENT_GUIDE.md` - Comprehensive deployment guide
- `README_DEPLOYMENT.md` - This quick start guide
- Existing guides for Civo and Kubernetes

✅ **Configuration**
- `.env.example` - Environment template
- `.dockerignore` files - Optimized builds
- Production Docker Compose file

## Features

### Backend (FastAPI)
- 416,310+ word dictionary
- Oxford Dictionary integration
- Real-time word validation
- Puzzle solver
- Advanced search with filters
- RESTful API with auto-generated docs

### Frontend (Angular + Material)
- Modern, glassmorphic UI
- Real-time statistics
- Hover-based interactions
- Synonym support
- Responsive design
- Three search modes: Basic, Advanced, Puzzle

## Troubleshooting

### Port Already in Use?
Edit `docker-compose.prod.yml` and change the port mappings:
```yaml
ports:
  - "8080:80"    # Frontend (change 8080 to any available port)
  - "8002:8001"  # Backend (change 8002 to any available port)
```

### Container Won't Start?
Check logs:
```bash
./deploy.sh logs
```

### Need to Reset Everything?
```bash
./deploy.sh clean
./deploy.sh up
```

## Next Steps

- Read `DEPLOYMENT_GUIDE.md` for detailed production deployment
- See `CIVO_DEPLOYMENT.md` for Civo Kubernetes deployment
- Review `civo-k8s/` directory for Civo Kubernetes manifests

## Support

For issues or questions:
1. Check the logs: `./deploy.sh logs`
2. Review `DEPLOYMENT_GUIDE.md`
3. Check existing documentation files

---

**Happy Deploying! 🎉**
