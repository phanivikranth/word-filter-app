# AWS EKS Deployment Guide

This guide will help you deploy your **Word Filter App** to Amazon EKS (Elastic Kubernetes Service) with Docker, Nginx, and managed Kubernetes.

## 📋 Prerequisites

### 1. Install Required Tools

**AWS CLI:**
```bash
# Windows (using Chocolatey)
choco install awscli

# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**kubectl:**
```bash
# Windows (using Chocolatey)
choco install kubernetes-cli

# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

**Docker Desktop:**
- Download from [docker.com](https://www.docker.com/products/docker-desktop)

**eksctl (optional but recommended):**
```bash
# Windows (using Chocolatey)
choco install eksctl

# macOS
brew tap weaveworks/tap
brew install eksctl

# Linux
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your:
# AWS Access Key ID
# AWS Secret Access Key
# Default region (e.g., us-west-2)
# Default output format (json)
```

## 🚀 Quick Setup (Using eksctl)

### 1. Create EKS Cluster

```bash
# Create cluster with eksctl (takes 10-15 minutes)
eksctl create cluster \
  --name word-filter-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed
```

### 2. Install Nginx Ingress Controller

```bash
# Add the ingress-nginx repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install nginx ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer
```

### 3. Install cert-manager (for SSL/TLS)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create a ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com # CHANGE THIS
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 4. Update Configuration

Update the following files with your specific information:

**scripts/build-and-deploy.sh** or **scripts/build-and-deploy.ps1:**
- Replace `your-account` with your AWS account ID
- Update `AWS_REGION` if different

**k8s/ingress.yaml:**
- Replace `word-filter.yourdomain.com` with your actual domain

## 🔧 Manual Setup (Using Terraform)

If you prefer Infrastructure as Code, use the Terraform configuration:

### 1. Initialize Terraform

```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### 2. Configure kubectl

```bash
aws eks update-kubeconfig --region us-west-2 --name word-filter-cluster
```

## 📦 Deploy Your Application

### Option 1: Automated Deployment

```bash
# Linux/macOS
chmod +x scripts/build-and-deploy.sh
./scripts/build-and-deploy.sh

# Windows
./scripts/build-and-deploy.ps1
```

### Option 2: Manual Deployment

```bash
# 1. Build and push Docker images
docker build -t your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:latest backend/
docker build -t your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-frontend:latest frontend/

# 2. Push to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-west-2.amazonaws.com
docker push your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:latest
docker push your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-frontend:latest

# 3. Deploy to Kubernetes
kubectl apply -f k8s/
```

## 🌐 Access Your Application

### Get the External IP

```bash
kubectl get ingress word-filter-ingress -n word-filter-app
```

### Configure DNS

Point your domain to the Load Balancer's external IP:

```
A record: word-filter.yourdomain.com -> [EXTERNAL-IP]
```

## 📊 Monitor Your Deployment

### Check Pod Status

```bash
kubectl get pods -n word-filter-app
kubectl logs -f deployment/word-filter-backend -n word-filter-app
kubectl logs -f deployment/word-filter-frontend -n word-filter-app
```

### View Services

```bash
kubectl get services -n word-filter-app
```

### Check Ingress

```bash
kubectl describe ingress word-filter-ingress -n word-filter-app
```

## 🔄 Updates and Rollbacks

### Update Application

```bash
# Build new images with version tag
docker build -t your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:v2.0 backend/
docker push your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:v2.0

# Update deployment
kubectl set image deployment/word-filter-backend backend=your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:v2.0 -n word-filter-app
```

### Rollback

```bash
kubectl rollout undo deployment/word-filter-backend -n word-filter-app
```

## 💰 Cost Optimization

### Auto Scaling

```bash
# Install cluster autoscaler
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# Configure HPA (Horizontal Pod Autoscaler)
kubectl autoscale deployment word-filter-backend --cpu-percent=50 --min=2 --max=10 -n word-filter-app
kubectl autoscale deployment word-filter-frontend --cpu-percent=50 --min=2 --max=10 -n word-filter-app
```

### Resource Optimization

Monitor and adjust resource requests/limits in your deployment files based on actual usage.

## 🧹 Cleanup

```bash
# Delete application
kubectl delete namespace word-filter-app

# Delete cluster (if using eksctl)
eksctl delete cluster --name word-filter-cluster --region us-west-2

# Or if using Terraform
cd terraform/
terraform destroy
```

## 🔐 Security Best Practices

1. **Use IAM roles for service accounts (IRSA)**
2. **Enable Pod Security Standards**
3. **Configure Network Policies**
4. **Use AWS Secrets Manager for sensitive data**
5. **Enable audit logging**
6. **Regularly update node AMIs**

## 📚 Useful Commands

```bash
# Scale deployments
kubectl scale deployment word-filter-backend --replicas=5 -n word-filter-app

# Port forward for testing
kubectl port-forward service/word-filter-backend 8001:8001 -n word-filter-app

# Execute into pod
kubectl exec -it deployment/word-filter-backend -n word-filter-app -- /bin/bash

# Get cluster info
kubectl cluster-info

# View node status
kubectl get nodes
```

## 🆘 Troubleshooting

### Common Issues

1. **ImagePullBackOff**: Check ECR permissions and image names
2. **CrashLoopBackOff**: Check application logs
3. **Service Unavailable**: Check ingress and service configurations
4. **DNS Issues**: Verify domain configuration and cert-manager

### Debug Commands

```bash
# Describe resources
kubectl describe pod [POD_NAME] -n word-filter-app
kubectl describe service [SERVICE_NAME] -n word-filter-app

# Check events
kubectl get events -n word-filter-app --sort-by='.lastTimestamp'

# Check ingress controller logs
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

---

## 🎉 Success!

Your Word Filter App is now running on AWS EKS with:
- ✅ High availability with multiple replicas
- ✅ Auto-scaling capabilities
- ✅ SSL/TLS encryption
- ✅ Professional domain
- ✅ Production-ready architecture

Access your app at: `https://word-filter.yourdomain.com`
