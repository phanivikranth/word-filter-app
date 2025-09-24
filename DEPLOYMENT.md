# 🚀 Kubernetes Deployment Guide

Your **Word Filter & Puzzle App** is now ready for production deployment on AWS EKS with Kubernetes!

## 📁 Project Structure

```
fullstack-app/
├── backend/
│   ├── Dockerfile                 # Backend container image
│   ├── .dockerignore
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile                 # Frontend container with Nginx
│   ├── nginx.conf                 # Nginx configuration
│   ├── .dockerignore
│   └── src/
├── k8s/
│   ├── namespace.yaml             # Kubernetes namespace
│   ├── backend-deployment.yaml    # Backend deployment & service
│   ├── frontend-deployment.yaml   # Frontend deployment & service
│   └── ingress.yaml              # Nginx ingress controller
├── scripts/
│   ├── build-and-deploy.sh       # Automated deployment (Linux/macOS)
│   └── build-and-deploy.ps1      # Automated deployment (Windows)
├── terraform/
│   ├── main.tf                   # EKS cluster infrastructure
│   ├── variables.tf              # Configuration variables
│   └── outputs.tf                # Infrastructure outputs
├── AWS_SETUP.md                  # Detailed AWS setup guide
└── DEPLOYMENT.md                 # This file
```

## 🏗️ Architecture

```
Internet → AWS Load Balancer → Nginx Ingress → Kubernetes Services
                                                      ↓
                                    Frontend Pods (Angular + Nginx)
                                    Backend Pods (FastAPI + Python)
```

### Components:
- **AWS EKS**: Managed Kubernetes cluster
- **ECR**: Private Docker registry
- **Application Load Balancer**: AWS load balancer via ingress
- **Nginx Ingress**: Routes traffic to appropriate services
- **Frontend**: Angular app served by Nginx (3 replicas)
- **Backend**: FastAPI application (3 replicas)
- **Auto-scaling**: Horizontal Pod Autoscaler configured

## ⚡ Quick Start

### 1. Prerequisites Check
```bash
# Verify tools are installed
docker --version
aws --version
kubectl version --client
```

### 2. One-Command Deployment
```bash
# Linux/macOS
chmod +x scripts/build-and-deploy.sh
./scripts/build-and-deploy.sh

# Windows PowerShell
./scripts/build-and-deploy.ps1
```

### 3. Access Your App
```bash
# Get the external URL
kubectl get ingress word-filter-ingress -n word-filter-app
```

## 🔧 Manual Deployment Steps

### Step 1: Set Up AWS Infrastructure

**Option A: Using eksctl (Recommended)**
```bash
eksctl create cluster --name word-filter-cluster --region us-west-2 --nodegroup-name standard-workers --node-type t3.medium --nodes 3 --managed
```

**Option B: Using Terraform**
```bash
cd terraform/
terraform init
terraform apply
aws eks update-kubeconfig --region us-west-2 --name word-filter-cluster
```

### Step 2: Install Ingress Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.service.type=LoadBalancer
```

### Step 3: Build and Push Docker Images
```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-west-2"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Create ECR repositories
aws ecr create-repository --repository-name word-filter-backend --region $AWS_REGION
aws ecr create-repository --repository-name word-filter-frontend --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push backend
cd backend
docker build -t ${ECR_REGISTRY}/word-filter-backend:latest .
docker push ${ECR_REGISTRY}/word-filter-backend:latest
cd ..

# Build and push frontend
cd frontend
docker build -t ${ECR_REGISTRY}/word-filter-frontend:latest .
docker push ${ECR_REGISTRY}/word-filter-frontend:latest
cd ..
```

### Step 4: Update Kubernetes Manifests
```bash
# Update image references with your ECR registry
sed -i "s|your-account.dkr.ecr.us-west-2.amazonaws.com|${ECR_REGISTRY}|g" k8s/backend-deployment.yaml
sed -i "s|your-account.dkr.ecr.us-west-2.amazonaws.com|${ECR_REGISTRY}|g" k8s/frontend-deployment.yaml
```

### Step 5: Deploy to Kubernetes
```bash
# Apply all manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n word-filter-app
kubectl get services -n word-filter-app
kubectl get ingress -n word-filter-app
```

## 📊 Production Features

### ✅ High Availability
- 3 replicas of each service
- Multiple availability zones
- Rolling updates with zero downtime
- Health checks and auto-restart

### ✅ Scalability
- Horizontal Pod Autoscaler
- Cluster Autoscaler
- Load balancing across pods
- Auto-scaling based on CPU/memory

### ✅ Security
- Private subnets for worker nodes
- Security groups and network policies
- SSL/TLS termination
- Container image scanning
- IAM roles and permissions

### ✅ Monitoring & Logging
- CloudWatch integration
- Kubernetes events
- Application logs
- Health check endpoints

### ✅ CI/CD Ready
- Automated build scripts
- Environment-based configuration
- Version tagging
- Easy rollbacks

## 🌐 DNS & SSL Configuration

### Configure Your Domain
1. Get the Load Balancer DNS name:
```bash
kubectl get ingress word-filter-ingress -n word-filter-app -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

2. Create a CNAME record in your DNS provider:
```
word-filter.yourdomain.com → [LOAD_BALANCER_DNS_NAME]
```

### Enable SSL (Let's Encrypt)
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Update k8s/ingress.yaml with your domain
# The certificate will be automatically provisioned
```

## 📈 Monitoring & Management

### View Application Status
```bash
# Pods
kubectl get pods -n word-filter-app -o wide

# Services
kubectl get svc -n word-filter-app

# Ingress
kubectl describe ingress word-filter-ingress -n word-filter-app
```

### Check Logs
```bash
# Backend logs
kubectl logs -f deployment/word-filter-backend -n word-filter-app

# Frontend logs
kubectl logs -f deployment/word-filter-frontend -n word-filter-app

# Ingress controller logs
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

### Scaling
```bash
# Manual scaling
kubectl scale deployment word-filter-backend --replicas=5 -n word-filter-app

# Auto-scaling
kubectl autoscale deployment word-filter-backend --cpu-percent=50 --min=2 --max=10 -n word-filter-app
```

## 🔄 Updates & Rollbacks

### Deploy New Version
```bash
# Build new image with version tag
docker build -t ${ECR_REGISTRY}/word-filter-backend:v2.0 backend/
docker push ${ECR_REGISTRY}/word-filter-backend:v2.0

# Update deployment
kubectl set image deployment/word-filter-backend backend=${ECR_REGISTRY}/word-filter-backend:v2.0 -n word-filter-app

# Monitor rollout
kubectl rollout status deployment/word-filter-backend -n word-filter-app
```

### Rollback if Needed
```bash
# Check rollout history
kubectl rollout history deployment/word-filter-backend -n word-filter-app

# Rollback to previous version
kubectl rollout undo deployment/word-filter-backend -n word-filter-app
```

## 💰 Cost Optimization

### Resource Limits
Your deployments include resource limits to optimize costs:
- **Backend**: 128Mi-512Mi memory, 100m-500m CPU
- **Frontend**: 64Mi-256Mi memory, 50m-250m CPU

### Auto Scaling
- Cluster autoscaler reduces nodes when demand is low
- HPA scales pods based on actual usage
- Scheduled scaling for predictable traffic patterns

## 🆘 Troubleshooting

### Common Issues

**Pods in ImagePullBackOff:**
```bash
# Check if ECR registry URL is correct
kubectl describe pod [POD_NAME] -n word-filter-app
```

**Service Unavailable (503):**
```bash
# Check ingress configuration
kubectl describe ingress word-filter-ingress -n word-filter-app

# Verify backend is running
kubectl get endpoints -n word-filter-app
```

**SSL Certificate Issues:**
```bash
# Check cert-manager logs
kubectl logs -f deployment/cert-manager -n cert-manager

# Verify certificate
kubectl describe certificate word-filter-tls -n word-filter-app
```

### Debug Commands
```bash
# Execute into a pod
kubectl exec -it deployment/word-filter-backend -n word-filter-app -- /bin/bash

# Port forward for local testing
kubectl port-forward service/word-filter-backend 8001:8001 -n word-filter-app

# View events
kubectl get events -n word-filter-app --sort-by='.lastTimestamp'
```

## 🧹 Cleanup

### Delete Application
```bash
kubectl delete namespace word-filter-app
```

### Delete Cluster
```bash
# If using eksctl
eksctl delete cluster --name word-filter-cluster --region us-west-2

# If using Terraform
cd terraform/
terraform destroy
```

## 🎯 Performance Tuning

### Optimize Docker Images
- Multi-stage builds for smaller images
- Use Alpine Linux base images
- Minimize layers and dependencies

### Kubernetes Optimizations
- Set appropriate resource requests/limits
- Use node affinity for better pod placement
- Configure pod disruption budgets
- Implement readiness and liveness probes

## 🎉 Success Metrics

Your app is successfully deployed when:
- ✅ All pods are in `Running` state
- ✅ Services have endpoints
- ✅ Ingress shows external IP
- ✅ Domain resolves to your app
- ✅ SSL certificate is valid
- ✅ Both frontend and backend are accessible

**Your Word Filter App is now running on production-grade Kubernetes infrastructure!** 🚀

Access it at: `https://word-filter.yourdomain.com`
