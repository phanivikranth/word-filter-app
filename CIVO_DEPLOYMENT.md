# Civo Cloud Deployment Guide

This guide covers deploying the Word Filter Application to Civo Cloud, a developer-friendly cloud provider offering Kubernetes-as-a-Service with competitive pricing and excellent performance.

## 🚀 Quick Start

The fastest way to deploy to Civo:

```bash
# 1. Install prerequisites
./scripts/civo/deploy-to-civo.sh --help

# 2. Deploy minimal setup for testing
./scripts/civo/deploy-to-civo.sh -e dev -t minimal

# 3. Deploy full production setup
./scripts/civo/deploy-to-civo.sh -e prod -t full -f
```

## 📋 Prerequisites

### Required Tools
- [Civo CLI](https://github.com/civo/cli) - Civo command line interface
- [Terraform](https://terraform.io) - Infrastructure as Code
- [kubectl](https://kubernetes.io/docs/tasks/tools/) - Kubernetes CLI
- [jq](https://stedolan.github.io/jq/) - JSON processor (for scripts)

### Installation Commands
```bash
# Install Civo CLI (Linux/macOS)
curl -sL https://github.com/civo/cli/releases/download/v1.0.0/civo-1.0.0-linux-amd64.tar.gz | tar xz
sudo mv civo /usr/local/bin/

# Install Civo CLI (Windows)
# Download from: https://github.com/civo/cli/releases

# Verify installation
civo version
```

### Authentication
```bash
# Get your API key from: https://dashboard.civo.com/account/api-keys
civo apikey save my-key YOUR_API_KEY_HERE
civo apikey current
```

## 🏗️ Infrastructure Options

### 1. Minimal Deployment (~$11/month)
Perfect for development and testing:
- **Cluster**: 1 small node (1 CPU, 2GB RAM)
- **Storage**: 50GB object store
- **Network**: Basic firewall rules
- **Services**: NodePort (no load balancer)

```bash
# Deploy minimal setup
cd civo-terraform-minimal
terraform init
terraform apply -var="cluster_name=word-filter-test"
```

### 2. Full Production Deployment (~$75/month)
Recommended for production workloads:
- **Cluster**: 3 medium nodes (2 CPU, 4GB RAM each)
- **Storage**: 500GB object store + persistent volumes
- **Network**: Advanced firewall + load balancer
- **Services**: LoadBalancer with SSL/TLS
- **Monitoring**: Prometheus + Grafana
- **Backup**: Automated backup system

```bash
# Deploy full production setup
cd civo-terraform
terraform apply -var="cluster_name=word-filter-prod" -var="environment=production"
```

### 3. Object Store Optimized (~$55/month)
Best for large word datasets:
- **Cluster**: 2 medium nodes
- **Storage**: Large object store + caching
- **Features**: Advanced word management, Oxford API integration
- **Performance**: Optimized for large datasets

```bash
# Deploy object store optimized
cd civo-terraform
terraform apply -var="deployment_type=objectstore"
```

## 🛠️ Deployment Methods

### Method 1: Automated Script (Recommended)

```bash
# PowerShell (Windows)
.\scripts\civo\deploy-to-civo.ps1 -Environment prod -DeploymentType full

# Bash (Linux/macOS)  
./scripts/civo/deploy-to-civo.sh -e prod -t full -f
```

**Script Options:**
- `-e, --environment`: dev, staging, prod
- `-t, --type`: minimal, full, objectstore  
- `-r, --region`: LON1, NYC1, FRA1
- `-f, --force`: Skip confirmation prompts
- `-n, --dry-run`: Preview changes without applying

### Method 2: Manual Terraform

```bash
# 1. Choose configuration
cd civo-terraform  # or civo-terraform-minimal

# 2. Initialize
terraform init

# 3. Plan deployment
terraform plan -var="cluster_name=my-cluster" -var="civo_region=LON1"

# 4. Apply
terraform apply -var="cluster_name=my-cluster" -var="civo_region=LON1"

# 5. Get kubeconfig
terraform output -raw kubeconfig > kubeconfig-civo.yaml
export KUBECONFIG=$PWD/kubeconfig-civo.yaml
```

### Method 3: GitHub Actions CI/CD

Trigger via GitHub Actions:
- **Manual**: Go to Actions → Deploy to Civo → Run workflow
- **Automatic**: Push to main branch (if enabled)

```yaml
# .github/workflows/deploy-civo.yml
# Supports multiple environments and deployment types
```

### Method 4: Multi-Cloud Deployment

Deploy to both AWS and Civo simultaneously:

```bash
# Deploy to both clouds
.\scripts\deploy-multi-cloud.ps1 -CloudProvider both -Environment prod

# Deploy only to Civo
.\scripts\deploy-multi-cloud.ps1 -CloudProvider civo -Environment prod
```

## 🌍 Regional Options

### Available Regions
- **LON1** (London, UK) - Recommended, lowest latency to Europe
- **NYC1** (New York, US) - Best for North America
- **FRA1** (Frankfurt, Germany) - Alternative European option

### Cost Comparison
All regions have the same pricing structure:

| Instance Type | CPU | RAM | Storage | Price/Month |
|---------------|-----|-----|---------|-------------|
| g4s.kube.small | 1 | 2GB | 25GB | $10.37 |
| g4s.kube.medium | 2 | 4GB | 40GB | $20.73 |
| g4s.kube.large | 4 | 8GB | 80GB | $41.46 |
| g4s.kube.xlarge | 6 | 16GB | 160GB | $82.92 |

## 📦 Application Configurations

### Basic Configuration (civo-k8s-minimal)
- Simple deployment with NodePort services
- Local file storage
- Single replica of each service
- Suitable for development/testing

### Full Configuration (civo-k8s)
- LoadBalancer services
- Multiple replicas for high availability
- Advanced health checks and monitoring
- Production-ready security settings

### Object Store Configuration (civo-k8s-objectstore)
- Civo Object Store integration
- S3-compatible API for word management
- Automated backup and sync
- Scalable word dataset management

## 🔧 Configuration Variables

### Terraform Variables
```hcl
# civo-terraform/terraform.tfvars
cluster_name = "word-filter-prod"
civo_region = "LON1"
environment = "production"
node_count = 3
node_size = "g4s.kube.medium"
objectstore_max_size_gb = 500
enable_monitoring = true
enable_database = false
```

### Kubernetes ConfigMaps
```yaml
# Update civo-k8s/configmap.yaml
CORS_ORIGINS: "https://your-domain.com"
LOG_LEVEL: "INFO"
ENABLE_OXFORD_VALIDATION: "true"
```

## 🔐 Security Setup

### 1. Object Store Credentials
```bash
# Create secret for object store access
kubectl create secret generic civo-objectstore-credentials \
  --from-literal=ACCESS_KEY_ID="your-access-key" \
  --from-literal=SECRET_ACCESS_KEY="your-secret-key" \
  -n word-filter-app
```

### 2. SSL/TLS Certificates
```bash
# Install cert-manager (included in full deployment)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Configure Let's Encrypt issuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
EOF
```

### 3. Network Policies
```bash
# Enable network policies (included in full deployment)
kubectl apply -f civo-k8s/network-policies.yaml
```

## 📊 Monitoring and Observability

### Built-in Monitoring (Full Deployment)
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Alertmanager**: Alert notifications

### Access Monitoring
```bash
# Get monitoring URLs
kubectl get services -n monitoring

# Port forward to access locally
kubectl port-forward -n monitoring service/grafana 3000:80
# Open http://localhost:3000 (admin/admin)
```

### Custom Dashboards
Pre-configured dashboards include:
- Application performance metrics
- Kubernetes cluster health
- Word processing statistics
- API endpoint monitoring

## 🔄 Backup and Recovery

### Automated Backups
```bash
# Enable backups in terraform
variable "enable_backups" {
  default = true
}

variable "backup_retention_days" {
  default = 30
}
```

### Manual Backup
```bash
# Backup word data
kubectl exec -n word-filter-app deployment/word-filter-backend -- \
  curl -X POST http://localhost:8001/words/backup

# Backup Kubernetes resources
kubectl get all -n word-filter-app -o yaml > backup-$(date +%Y%m%d).yaml
```

### Disaster Recovery
```bash
# Restore from backup
kubectl apply -f backup-YYYYMMDD.yaml

# Restore word data (if using object store)
# Data is automatically restored from object store on pod restart
kubectl rollout restart deployment/word-filter-backend -n word-filter-app
```

## 🚦 Health Checks and Troubleshooting

### Health Check Commands
```bash
# Check cluster status
kubectl get nodes
kubectl get pods -n word-filter-app

# Check application health
kubectl logs -n word-filter-app -l app=word-filter-backend
kubectl logs -n word-filter-app -l app=word-filter-frontend

# Test API endpoints
kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001
curl http://localhost:8001/health
curl http://localhost:8001/words/stats
```

### Common Issues and Solutions

#### 1. Pod Stuck in Pending State
```bash
# Check node resources
kubectl describe nodes
kubectl top nodes

# Check pod events
kubectl describe pod -n word-filter-app POD_NAME
```

**Solution**: Usually indicates insufficient cluster resources. Scale up nodes:
```bash
# Update node count in Terraform
terraform apply -var="node_count=4"
```

#### 2. Object Store Connection Issues
```bash
# Check credentials
kubectl get secret civo-objectstore-credentials -n word-filter-app -o yaml

# Check configuration
kubectl get configmap civo-objectstore-config -n word-filter-app -o yaml
```

**Solution**: Verify credentials and endpoint URL:
```bash
# Update credentials
kubectl patch secret civo-objectstore-credentials -n word-filter-app \
  --type merge -p='{"data":{"ACCESS_KEY_ID":"NEW_KEY_BASE64"}}'
```

#### 3. LoadBalancer IP Pending
```bash
# Check service status
kubectl get services -n word-filter-app
kubectl describe service word-filter-backend -n word-filter-app
```

**Solution**: Civo LoadBalancers take 2-3 minutes to provision. If stuck:
```bash
# Delete and recreate service
kubectl delete service word-filter-backend -n word-filter-app
kubectl apply -f civo-k8s/backend-deployment.yaml
```

#### 4. High Memory Usage
```bash
# Check resource usage
kubectl top pods -n word-filter-app
kubectl describe pod -n word-filter-app POD_NAME
```

**Solution**: Increase resource limits or optimize word loading:
```bash
# Update resource limits
kubectl patch deployment word-filter-backend -n word-filter-app -p='
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "backend",
          "resources": {
            "limits": {"memory": "2Gi"}
          }
        }]
      }
    }
  }
}'
```

## 📈 Scaling and Optimization

### Horizontal Scaling
```bash
# Scale backend pods
kubectl scale deployment word-filter-backend -n word-filter-app --replicas=5

# Scale frontend pods  
kubectl scale deployment word-filter-frontend -n word-filter-app --replicas=3
```

### Auto-scaling
```bash
# Enable Horizontal Pod Autoscaler
kubectl autoscale deployment word-filter-backend -n word-filter-app \
  --cpu-percent=70 --min=2 --max=10
```

### Vertical Scaling
```bash
# Update node size in Terraform
terraform apply -var="node_size=g4s.kube.large"
```

## 💰 Cost Optimization

### Development Environment
- Use `minimal` deployment type
- Single node cluster
- Smaller object store allocation
- **Estimated cost**: ~$11/month

### Staging Environment
- Use `full` deployment with fewer replicas
- 2 medium nodes
- Moderate object store size
- **Estimated cost**: ~$45/month

### Production Environment
- Use `full` or `objectstore` deployment
- 3+ medium/large nodes
- Full monitoring and backup
- **Estimated cost**: $75-150/month

### Cost Monitoring
```bash
# Get cost estimate from Terraform
terraform plan -out=plan
terraform show -json plan | jq '.configuration.root_module.variables.estimated_monthly_cost'
```

## 🔄 Updates and Maintenance

### Application Updates
```bash
# Update application images
kubectl set image deployment/word-filter-backend backend=phanivikranth/word-filter-backend:v2.0 -n word-filter-app
kubectl set image deployment/word-filter-frontend frontend=phanivikranth/word-filter-frontend:v2.0 -n word-filter-app

# Check rollout status
kubectl rollout status deployment/word-filter-backend -n word-filter-app
```

### Infrastructure Updates
```bash
# Update Terraform configuration
cd civo-terraform
terraform plan
terraform apply

# Update Kubernetes manifests
kubectl apply -f civo-k8s/
```

### Cluster Maintenance
```bash
# Drain node for maintenance
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data

# Uncordon node after maintenance
kubectl uncordon NODE_NAME
```

## 🌐 Domain and DNS Setup

### Using Civo DNS
```bash
# Add domain to Civo (if you have a domain managed by Civo)
civo dns domain-record create your-domain.com -n word-filter -t A -v LOAD_BALANCER_IP

# Update Terraform for automatic DNS
terraform apply -var="domain_name=your-domain.com" -var="subdomain=word-filter"
```

### Using External DNS
```yaml
# Update ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: word-filter-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - word-filter.your-domain.com
    secretName: word-filter-tls
  rules:
  - host: word-filter.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: word-filter-frontend
            port:
              number: 80
```

## 📞 Support and Community

### Civo Support
- **Documentation**: https://www.civo.com/docs
- **Community**: https://community.civo.com
- **Support**: https://www.civo.com/support
- **Status**: https://status.civo.com

### Word Filter App Support
- **GitHub Issues**: https://github.com/phanivikranth/word-filter-app/issues
- **Discussions**: https://github.com/phanivikranth/word-filter-app/discussions

### Useful Links
- [Civo CLI Documentation](https://github.com/civo/cli)
- [Kubernetes Documentation](https://kubernetes.io/docs)
- [Terraform Civo Provider](https://registry.terraform.io/providers/civo/civo/latest/docs)
- [Traefik Ingress Controller](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)

## 🎯 Next Steps

After successful deployment:

1. **Configure Domain**: Set up your domain and SSL certificates
2. **Set up Monitoring**: Configure alerts and dashboards
3. **Load Test**: Verify performance under load
4. **Backup Strategy**: Implement and test backup/restore procedures
5. **CI/CD Integration**: Set up automated deployments
6. **Security Hardening**: Review and implement additional security measures

## 📝 Example Workflows

### Development Workflow
```bash
# 1. Deploy minimal environment
./scripts/civo/deploy-to-civo.sh -e dev -t minimal

# 2. Port forward for local development
kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001 &
kubectl port-forward -n word-filter-app service/word-filter-frontend 4201:80 &

# 3. Test changes
curl http://localhost:8001/health
open http://localhost:4201

# 4. Clean up when done
terraform destroy -auto-approve
```

### Production Workflow
```bash
# 1. Deploy production infrastructure
./scripts/civo/deploy-to-civo.sh -e prod -t objectstore -f

# 2. Configure domain and SSL
kubectl apply -f production-ingress.yaml

# 3. Set up monitoring
kubectl apply -f monitoring/

# 4. Configure backups
kubectl apply -f backup-cronjob.yaml

# 5. Monitor deployment
kubectl get pods -n word-filter-app -w
```

This completes your Civo Cloud deployment guide. Your Word Filter Application is now ready to run on Civo with full multi-cloud support! 🚀
