#!/bin/bash

# Minimal Testing Deployment Script
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_options() {
    echo "🧪 Word Filter App - Testing Deployment Options"
    echo ""
    echo "Choose your testing method:"
    echo "1. Docker Compose (Simplest - no Kubernetes)"
    echo "2. Kind (Local Kubernetes)"
    echo "3. AWS EKS Minimal (Cloud testing - ~$30-50/month)"
    echo "4. Development servers (No containers)"
    echo ""
}

docker_compose_test() {
    log_info "Starting Docker Compose testing environment..."
    
    # Build and start services
    docker-compose -f docker-compose.test.yml down --remove-orphans
    docker-compose -f docker-compose.test.yml build
    docker-compose -f docker-compose.test.yml up -d
    
    # Wait for services
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check health
    if curl -s http://localhost:8001/ > /dev/null; then
        log_success "Backend is running on http://localhost:8001"
        log_success "API docs: http://localhost:8001/docs"
    else
        log_error "Backend health check failed"
    fi
    
    if curl -s http://localhost/ > /dev/null; then
        log_success "Full app is running on http://localhost"
    else
        log_error "Frontend health check failed"
    fi
    
    log_info "To view logs: docker-compose -f docker-compose.test.yml logs -f"
    log_info "To stop: docker-compose -f docker-compose.test.yml down"
}

kind_test() {
    log_info "Setting up Kind (local Kubernetes)..."
    
    # Check if kind is installed
    if ! command -v kind &> /dev/null; then
        log_error "Kind is not installed. Install with:"
        echo "  # Linux"
        echo "  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
        echo "  chmod +x ./kind"
        echo "  sudo mv ./kind /usr/local/bin/kind"
        echo ""
        echo "  # Windows (Chocolatey)"
        echo "  choco install kind"
        echo ""
        echo "  # macOS"
        echo "  brew install kind"
        exit 1
    fi
    
    # Create cluster
    log_info "Creating Kind cluster..."
    kind delete cluster --name word-filter-test 2>/dev/null || true
    kind create cluster --config kind-config.yaml
    
    # Install nginx ingress
    log_info "Installing nginx ingress..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s
    
    # Build and load images
    log_info "Building and loading Docker images..."
    docker build -t word-filter-backend:test backend/
    docker build -t word-filter-frontend:test frontend/
    
    kind load docker-image word-filter-backend:test --name word-filter-test
    kind load docker-image word-filter-frontend:test --name word-filter-test
    
    # Update image references in manifests
    sed -i.bak 's|your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:latest|word-filter-backend:test|g' k8s-minimal/backend-deployment.yaml
    sed -i.bak 's|your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-frontend:latest|word-filter-frontend:test|g' k8s-minimal/frontend-deployment.yaml
    
    # Deploy application
    log_info "Deploying application..."
    kubectl apply -f k8s-minimal/
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/word-filter-backend -n word-filter-test
    kubectl wait --for=condition=available --timeout=300s deployment/word-filter-frontend -n word-filter-test
    
    log_success "Application deployed to Kind!"
    log_success "Access at: http://localhost:8080"
    log_info "API docs: http://localhost:8080/docs"
    
    log_info "To check status:"
    echo "  kubectl get pods -n word-filter-test"
    echo "  kubectl logs -f deployment/word-filter-backend -n word-filter-test"
    
    log_info "To cleanup:"
    echo "  kind delete cluster --name word-filter-test"
}

aws_minimal_test() {
    log_warning "AWS EKS Minimal will create real AWS resources and cost money!"
    log_warning "Estimated cost: $30-50/month"
    read -p "Continue? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled"
        exit 0
    fi
    
    log_info "Setting up minimal EKS cluster..."
    
    # Check prerequisites
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Deploy infrastructure
    cd terraform-minimal/
    terraform init
    terraform plan
    terraform apply -auto-approve
    
    # Update kubeconfig
    CLUSTER_NAME=$(terraform output -raw cluster_name)
    aws eks update-kubeconfig --region us-west-2 --name $CLUSTER_NAME
    
    # Get ECR URLs
    ECR_BACKEND=$(terraform output -raw ecr_backend_repository_url)
    ECR_FRONTEND=$(terraform output -raw ecr_frontend_repository_url)
    
    cd ..
    
    # Build and push images
    log_info "Building and pushing Docker images..."
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(echo $ECR_BACKEND | cut -d'/' -f1)
    
    docker build -t $ECR_BACKEND:latest backend/
    docker build -t $ECR_FRONTEND:latest frontend/
    
    docker push $ECR_BACKEND:latest
    docker push $ECR_FRONTEND:latest
    
    # Update manifests
    sed -i.bak "s|your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-backend:latest|$ECR_BACKEND:latest|g" k8s-minimal/backend-deployment.yaml
    sed -i.bak "s|your-account.dkr.ecr.us-west-2.amazonaws.com/word-filter-frontend:latest|$ECR_FRONTEND:latest|g" k8s-minimal/frontend-deployment.yaml
    
    # Install nginx ingress
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.service.type=LoadBalancer
    
    # Deploy application
    kubectl apply -f k8s-minimal/
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-backend -n word-filter-test
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-frontend -n word-filter-test
    
    # Get URL
    EXTERNAL_IP=$(kubectl get ingress word-filter-ingress -n word-filter-test -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    log_success "Application deployed to AWS EKS!"
    log_success "URL: http://$EXTERNAL_IP"
    log_warning "Don't forget to destroy resources when done:"
    echo "  cd terraform-minimal/ && terraform destroy"
}

dev_test() {
    log_info "Starting development servers (no containers)..."
    
    # Check if servers are already running
    if curl -s http://localhost:8001/ > /dev/null; then
        log_success "Backend already running on http://localhost:8001"
    else
        log_info "Start backend manually:"
        echo "  cd backend && ./venv/Scripts/activate && python main.py"
    fi
    
    if curl -s http://localhost:4201/ > /dev/null; then
        log_success "Frontend already running on http://localhost:4201"
    else
        log_info "Start frontend manually:"
        echo "  cd frontend && npm start"
    fi
    
    log_info "Access app at: http://localhost:4201"
}

# Main menu
case "${1:-menu}" in
    "1"|"docker"|"compose")
        docker_compose_test
        ;;
    "2"|"kind"|"local")
        kind_test
        ;;
    "3"|"aws"|"minimal")
        aws_minimal_test
        ;;
    "4"|"dev"|"development")
        dev_test
        ;;
    "menu"|*)
        show_options
        read -p "Choose option (1-4): " choice
        case $choice in
            1) docker_compose_test ;;
            2) kind_test ;;
            3) aws_minimal_test ;;
            4) dev_test ;;
            *) log_error "Invalid option" ;;
        esac
        ;;
esac
