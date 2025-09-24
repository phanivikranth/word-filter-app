#!/bin/bash

# Word Filter App - Build and Deploy Script
# This script builds Docker images, pushes to AWS ECR, and deploys to EKS

set -e

# Configuration
AWS_REGION="us-west-2"
ECR_REGISTRY="your-account.dkr.ecr.${AWS_REGION}.amazonaws.com"
APP_NAME="word-filter"
NAMESPACE="word-filter-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    
    log_success "All prerequisites met"
}

create_ecr_repositories() {
    log_info "Creating ECR repositories..."
    
    # Create backend repository
    aws ecr describe-repositories --repository-names "${APP_NAME}-backend" --region $AWS_REGION &> /dev/null || {
        log_info "Creating backend ECR repository..."
        aws ecr create-repository --repository-name "${APP_NAME}-backend" --region $AWS_REGION
    }
    
    # Create frontend repository
    aws ecr describe-repositories --repository-names "${APP_NAME}-frontend" --region $AWS_REGION &> /dev/null || {
        log_info "Creating frontend ECR repository..."
        aws ecr create-repository --repository-name "${APP_NAME}-frontend" --region $AWS_REGION
    }
    
    log_success "ECR repositories ready"
}

build_images() {
    log_info "Building Docker images..."
    
    # Get ECR login token
    log_info "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build backend image
    log_info "Building backend image..."
    cd backend
    docker build -t "${ECR_REGISTRY}/${APP_NAME}-backend:latest" .
    cd ..
    
    # Build frontend image
    log_info "Building frontend image..."
    cd frontend
    docker build -t "${ECR_REGISTRY}/${APP_NAME}-frontend:latest" .
    cd ..
    
    log_success "Docker images built successfully"
}

push_images() {
    log_info "Pushing images to ECR..."
    
    docker push "${ECR_REGISTRY}/${APP_NAME}-backend:latest"
    docker push "${ECR_REGISTRY}/${APP_NAME}-frontend:latest"
    
    log_success "Images pushed to ECR"
}

deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Update kubeconfig
    log_info "Updating kubeconfig..."
    aws eks update-kubeconfig --region $AWS_REGION --name word-filter-cluster
    
    # Create namespace
    log_info "Creating namespace..."
    kubectl apply -f k8s/namespace.yaml
    
    # Update image references in deployment files
    log_info "Updating image references..."
    sed -i.bak "s|your-account.dkr.ecr.us-west-2.amazonaws.com|${ECR_REGISTRY}|g" k8s/backend-deployment.yaml
    sed -i.bak "s|your-account.dkr.ecr.us-west-2.amazonaws.com|${ECR_REGISTRY}|g" k8s/frontend-deployment.yaml
    
    # Apply Kubernetes manifests
    log_info "Applying backend deployment..."
    kubectl apply -f k8s/backend-deployment.yaml
    
    log_info "Applying frontend deployment..."
    kubectl apply -f k8s/frontend-deployment.yaml
    
    log_info "Applying ingress..."
    kubectl apply -f k8s/ingress.yaml
    
    # Wait for deployments
    log_info "Waiting for backend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-backend -n $NAMESPACE
    
    log_info "Waiting for frontend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-frontend -n $NAMESPACE
    
    log_success "Deployment completed successfully"
}

show_status() {
    log_info "Deployment Status:"
    
    echo ""
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
    
    echo ""
    echo "Services:"
    kubectl get services -n $NAMESPACE
    
    echo ""
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    
    echo ""
    log_info "To get the external IP address:"
    echo "kubectl get ingress word-filter-ingress -n $NAMESPACE"
    
    echo ""
    log_info "To check logs:"
    echo "kubectl logs -f deployment/word-filter-backend -n $NAMESPACE"
    echo "kubectl logs -f deployment/word-filter-frontend -n $NAMESPACE"
}

# Main execution
main() {
    log_info "Starting Word Filter App deployment..."
    
    check_prerequisites
    create_ecr_repositories
    build_images
    push_images
    deploy_to_kubernetes
    show_status
    
    log_success "Deployment pipeline completed!"
    log_info "Your app should be accessible via the ingress URL once DNS propagates"
}

# Parse command line arguments
case "${1:-deploy}" in
    "build")
        log_info "Building images only..."
        check_prerequisites
        build_images
        ;;
    "push")
        log_info "Pushing images only..."
        check_prerequisites
        push_images
        ;;
    "deploy")
        main
        ;;
    "status")
        show_status
        ;;
    *)
        echo "Usage: $0 {build|push|deploy|status}"
        echo "  build  - Build Docker images only"
        echo "  push   - Push images to ECR only"
        echo "  deploy - Full deployment pipeline (default)"
        echo "  status - Show deployment status"
        exit 1
        ;;
esac
