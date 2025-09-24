#!/bin/bash

# Word Filter App - S3 Integration Setup Script
# This script sets up S3 bucket and deploys the app with dynamic word management

set -e

# Configuration
AWS_REGION="us-west-2"
BUCKET_NAME="word-filter-storage-$(date +%s)"  # Unique bucket name
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
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check if kubectl is configured
    if ! kubectl version &> /dev/null; then
        log_error "kubectl not configured or cluster not accessible"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

create_s3_bucket() {
    log_info "Creating S3 bucket: $BUCKET_NAME"
    
    # Create bucket
    aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket $BUCKET_NAME \
        --versioning-configuration Status=Enabled
    
    # Set public access block (security)
    aws s3api put-public-access-block \
        --bucket $BUCKET_NAME \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    log_success "S3 bucket created: $BUCKET_NAME"
}

upload_initial_words() {
    log_info "Uploading initial words file to S3..."
    
    # Check if local words.txt exists
    if [ -f "backend/words.txt" ]; then
        aws s3 cp backend/words.txt s3://$BUCKET_NAME/words/words.txt
        log_success "Uploaded words.txt to S3"
    else
        log_warning "No local words.txt found. App will create default words."
    fi
}

create_iam_policy() {
    log_info "Creating IAM policy for S3 access..."
    
    # Create IAM policy for S3 access
    POLICY_NAME="WordFilterS3Policy-$(date +%s)"
    
    cat > /tmp/s3-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${BUCKET_NAME}",
                "arn:aws:s3:::${BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF
    
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file:///tmp/s3-policy.json
    
    log_success "IAM policy created: $POLICY_NAME"
    echo "Policy ARN: arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/$POLICY_NAME"
}

update_kubernetes_config() {
    log_info "Updating Kubernetes configuration..."
    
    # Update ConfigMap with actual bucket name
    sed -i.bak "s/word-filter-storage/$BUCKET_NAME/g" k8s-s3/configmap.yaml
    
    # Get AWS credentials
    AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
    AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
    
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        # Encode credentials
        ENCODED_ACCESS_KEY=$(echo -n "$AWS_ACCESS_KEY_ID" | base64)
        ENCODED_SECRET_KEY=$(echo -n "$AWS_SECRET_ACCESS_KEY" | base64)
        
        # Update Secret
        sed -i.bak "s/eW91ci1hY2Nlc3Mta2V5LWlkLWhlcmU=/$ENCODED_ACCESS_KEY/g" k8s-s3/configmap.yaml
        sed -i.bak "s/eW91ci1zZWNyZXQtYWNjZXNzLWtleS1oZXJl/$ENCODED_SECRET_KEY/g" k8s-s3/configmap.yaml
        
        log_success "Updated Kubernetes configuration with AWS credentials"
    else
        log_error "Could not retrieve AWS credentials"
        exit 1
    fi
}

build_and_push_image() {
    log_info "Building and pushing Docker image with S3 support..."
    
    # Build image using S3 Dockerfile
    cd backend
    docker build -f Dockerfile.s3 -t ${ECR_REGISTRY}/${APP_NAME}-backend:s3-latest .
    cd ..
    
    # Push to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    docker push ${ECR_REGISTRY}/${APP_NAME}-backend:s3-latest
    
    # Update deployment with new image tag
    sed -i.bak "s|${APP_NAME}-backend:latest|${APP_NAME}-backend:s3-latest|g" k8s-s3/backend-deployment.yaml
    
    log_success "Docker image built and pushed"
}

deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace
    kubectl apply -f k8s/namespace.yaml
    
    # Apply S3 configuration
    kubectl apply -f k8s-s3/configmap.yaml
    kubectl apply -f k8s-s3/backend-deployment.yaml
    kubectl apply -f k8s/frontend-deployment.yaml  # Frontend unchanged
    kubectl apply -f k8s/ingress.yaml  # Ingress unchanged
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/word-filter-backend -n $NAMESPACE
    
    log_success "Deployment completed"
}

test_s3_integration() {
    log_info "Testing S3 integration..."
    
    # Get backend pod name
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=word-filter-backend -o jsonpath='{.items[0].metadata.name}')
    
    # Test health endpoint
    kubectl port-forward pod/$POD_NAME -n $NAMESPACE 8001:8001 &
    PF_PID=$!
    sleep 5
    
    # Test API endpoints
    if curl -s http://localhost:8001/health | grep -q "healthy"; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
    fi
    
    # Test word addition
    curl -X POST http://localhost:8001/words/add \
         -H "Content-Type: application/json" \
         -d '{"word":"testing"}' | grep -q "success"
    
    if [ $? -eq 0 ]; then
        log_success "Word addition test passed"
    else
        log_warning "Word addition test failed"
    fi
    
    # Stop port forwarding
    kill $PF_PID
    
    log_success "S3 integration tests completed"
}

show_usage_examples() {
    log_info "S3 Integration Usage Examples:"
    
    echo ""
    echo "🔗 API Endpoints for Word Management:"
    echo "POST /words/add          - Add a single word"
    echo "POST /words/add-batch    - Add multiple words"
    echo "POST /words/check        - Check if word exists"
    echo "POST /words/reload       - Reload words from S3"
    echo "GET  /words/all          - Get all words (admin)"
    echo ""
    
    echo "📝 Example: Add a word"
    echo "curl -X POST http://your-app-url/words/add \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"word\":\"amazing\"}'"
    echo ""
    
    echo "📦 S3 Bucket Details:"
    echo "Bucket Name: $BUCKET_NAME"
    echo "Words File: s3://$BUCKET_NAME/words/words.txt"
    echo ""
    
    echo "🎯 Benefits:"
    echo "✅ Dynamic word updates without pod restart"
    echo "✅ Shared word list across all pod replicas"
    echo "✅ Persistent storage with versioning"
    echo "✅ Scalable architecture"
}

# Main execution
main() {
    log_info "Starting S3 Integration Setup..."
    
    check_prerequisites
    create_s3_bucket
    upload_initial_words
    create_iam_policy
    update_kubernetes_config
    build_and_push_image
    deploy_to_kubernetes
    test_s3_integration
    show_usage_examples
    
    log_success "S3 Integration Setup Complete!"
    log_info "Your app now supports dynamic word management via S3"
}

# Parse command line arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "bucket-only")
        check_prerequisites
        create_s3_bucket
        upload_initial_words
        log_success "S3 bucket setup complete"
        ;;
    "deploy-only")
        check_prerequisites
        build_and_push_image
        deploy_to_kubernetes
        log_success "Deployment complete"
        ;;
    "test")
        test_s3_integration
        ;;
    *)
        echo "Usage: $0 {setup|bucket-only|deploy-only|test}"
        echo "  setup       - Full S3 integration setup (default)"
        echo "  bucket-only - Create S3 bucket and upload words"
        echo "  deploy-only - Build and deploy app only"
        echo "  test        - Test S3 integration"
        exit 1
        ;;
esac
