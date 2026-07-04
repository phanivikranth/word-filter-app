# Word Filter Application - Deployment Guide

## 📦 Production Deployment Package

This guide covers deploying the Word Filter application using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- At least 2GB of available RAM
- At least 5GB of available disk space

## Quick Start

### 1. Clone or Extract the Repository

```bash
cd fullstack-app
```

### 2. Configure Environment

Copy the example environment file and edit it:

```bash
# Linux/Mac
cp .env.example .env

# Windows
copy .env.example .env
```

Edit `.env` and update the values:
- `CORS_ORIGINS`: Add your domain(s)
- Other configuration as needed

### 3. Deploy the Application

#### Linux/Mac:

```bash
# Make the script executable
chmod +x deploy.sh

# Deploy
./deploy.sh up
```

#### Windows (PowerShell):

```powershell
.\deploy.ps1 up
```

### 4. Access the Application

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## Deployment Commands

### Linux/Mac (`deploy.sh`)

```bash
./deploy.sh build    # Build Docker images
./deploy.sh up       # Start the application
./deploy.sh down     # Stop the application
./deploy.sh restart  # Restart the application
./deploy.sh logs     # View logs (follow mode)
./deploy.sh status   # Show container status
./deploy.sh clean    # Stop and remove everything
./deploy.sh rebuild  # Rebuild and restart
```

### Windows PowerShell (`deploy.ps1`)

```powershell
.\deploy.ps1 build
.\deploy.ps1 up
.\deploy.ps1 down
.\deploy.ps1 restart
.\deploy.ps1 logs
.\deploy.ps1 status
.\deploy.ps1 clean
.\deploy.ps1 rebuild
```

## Manual Docker Compose Commands

If you prefer to use Docker Compose directly:

```bash
# Start
docker compose -f docker-compose.prod.yml up -d

# Stop
docker compose -f docker-compose.prod.yml down

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Rebuild
docker compose -f docker-compose.prod.yml build --no-cache
```

## Production Deployment Options

### 1. Single Server Deployment

Use the provided `docker-compose.prod.yml` file on a single server.

**Recommended Specs:**
- 2 CPU cores
- 4GB RAM
- 20GB storage
- Ubuntu 20.04+ or similar Linux distribution

### 2. Kubernetes Deployment

Use the provided Kubernetes manifests in the `k8s/` directory:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
```

### 3. Cloud Provider Deployment

#### Civo Kubernetes
See `CIVO_DEPLOYMENT.md` for Civo-specific instructions.

## Configuration

### Backend Configuration

Edit `backend/main.py` or use environment variables:

- `ENVIRONMENT`: `production` or `development`
- `LOG_LEVEL`: `INFO`, `WARNING`, `ERROR`
- `CORS_ORIGINS`: Comma-separated list of allowed origins

### Frontend Configuration

Edit `frontend/src/environments/environment.prod.ts`:

```typescript
export const environment = {
  production: true,
  apiUrl: 'http://your-domain.com:8001'
};
```

Then rebuild the frontend:

```bash
cd frontend
npm run build
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Backend only
docker compose -f docker-compose.prod.yml logs -f backend

# Frontend only
docker compose -f docker-compose.prod.yml logs -f frontend
```

### Health Checks

The application includes built-in health checks:

- **Backend**: http://localhost:8001/words/stats
- **Frontend**: http://localhost/

### Log Files

Backend logs are stored in:
- Container: `/app/logs/`
- Host (via volume): `backend-logs` Docker volume

## Backup and Restore

### Backup Word Collection

```bash
# Backup words.txt
docker cp word-filter-backend:/app/words.txt ./backup-words-$(date +%Y%m%d).txt

# Or from host
cp backend/words.txt ./backup-words-$(date +%Y%m%d).txt
```

### Restore Word Collection

```bash
# Stop the application
./deploy.sh down

# Restore the file
cp backup-words-20250105.txt backend/words.txt

# Restart
./deploy.sh up
```

## Updating the Application

### Update Code

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
./deploy.sh rebuild
```

### Update Dependencies

#### Backend:
```bash
cd backend
# Update requirements.txt
# Then rebuild
cd ..
./deploy.sh rebuild
```

#### Frontend:
```bash
cd frontend
npm update
npm run build
cd ..
./deploy.sh rebuild
```

## Troubleshooting

### Port Already in Use

If ports 80 or 8001 are already in use, edit `docker-compose.prod.yml`:

```yaml
services:
  backend:
    ports:
      - "8002:8001"  # Change host port
  
  frontend:
    ports:
      - "8080:80"    # Change host port
```

### Container Won't Start

Check logs:
```bash
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs frontend
```

### Out of Memory

Increase Docker memory allocation:
- Docker Desktop: Settings → Resources → Memory
- Linux: Adjust system resources

### Permission Issues

On Linux, you may need to run with sudo:
```bash
sudo ./deploy.sh up
```

## Security Considerations

1. **Change Default Ports**: Don't expose ports 80/8001 directly in production
2. **Use HTTPS**: Set up a reverse proxy (Nginx/Traefik) with SSL
3. **Environment Variables**: Never commit `.env` to version control
4. **Update Dependencies**: Regularly update Docker images and dependencies
5. **Firewall**: Configure firewall rules to restrict access
6. **Secrets Management**: Use Docker secrets or vault for sensitive data

## Performance Tuning

### Backend Optimization

Edit `backend/main.py` to adjust:
- Worker processes
- Connection pool size
- Cache settings

### Frontend Optimization

The Angular app is already optimized with:
- AOT compilation
- Tree shaking
- Minification
- Gzip compression (via Nginx)

### Database/Storage

For large word collections (>1M words), consider:
- Using a database (PostgreSQL/MongoDB)
- Implementing Redis caching
- Sharding word data

## Scaling

### Horizontal Scaling

Use Docker Swarm or Kubernetes for multi-instance deployment:

```bash
# Docker Swarm example
docker swarm init
docker stack deploy -c docker-compose.prod.yml word-filter
```

### Load Balancing

Add a load balancer (Nginx/HAProxy) in front of multiple backend instances.

## Support and Resources

- **Documentation**: See other `.md` files in the repository
- **API Docs**: http://localhost:8001/docs (when running)
- **Issues**: Check logs and troubleshooting section above

## License

See `LICENSE` file for details.

---

**Last Updated**: October 2025
**Version**: 2.0.0
