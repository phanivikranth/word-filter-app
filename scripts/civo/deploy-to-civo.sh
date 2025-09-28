#!/bin/bash

# Bash script to deploy Word Filter App to Civo Cloud
# Usage: ./deploy-to-civo.sh [-e prod|dev] [-t minimal|full|objectstore] [-s] [-k] [-n] [-f]

set -e

# Default values
ENVIRONMENT="prod"
DEPLOYMENT_TYPE="full"
SKIP_TERRAFORM=false
SKIP_K8S=false
DRY_RUN=false
CIVO_REGION="LON1"
CLUSTER_NAME="word-filter-civo"
FORCE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_step() {
    echo -e "${BLUE}🚀 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV     Environment: prod, dev, staging (default: prod)"
    echo "  -t, --type TYPE           Deployment type: minimal, full, objectstore (default: full)"
    echo "  -s, --skip-terraform      Skip Terraform deployment"
    echo "  -k, --skip-k8s            Skip Kubernetes deployment"
    echo "  -n, --dry-run             Show what would be done without making changes"
    echo "  -r, --region REGION       Civo region (default: LON1)"
    echo "  -c, --cluster-name NAME   Cluster name (default: word-filter-civo)"
    echo "  -f, --force               Don't prompt for confirmation"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev -t minimal     # Deploy minimal development environment"
    echo "  $0 -e prod -t objectstore -f  # Deploy production with object store, no prompts"
    echo "  $0 -n                    # Dry run with default settings"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -s|--skip-terraform)
            SKIP_TERRAFORM=true
            shift
            ;;
        -k|--skip-k8s)
            SKIP_K8S=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -r|--region)
            CIVO_REGION="$2"
            shift 2
            ;;
        -c|--cluster-name)
            CLUSTER_NAME="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate arguments
case $ENVIRONMENT in
    prod|dev|staging)
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        echo "Valid environments: prod, dev, staging"
        exit 1
        ;;
esac

case $DEPLOYMENT_TYPE in
    minimal|full|objectstore)
        ;;
    *)
        log_error "Invalid deployment type: $DEPLOYMENT_TYPE"
        echo "Valid deployment types: minimal, full, objectstore"
        exit 1
        ;;
esac

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Test prerequisites
test_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing=()
    
    if ! command_exists terraform; then
        missing+=("terraform")
    fi
    
    if ! command_exists kubectl; then
        missing+=("kubectl")
    fi
    
    if ! command_exists civo; then
        missing+=("civo CLI")
    fi
    
    if ! command_exists jq; then
        missing+=("jq")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        echo "Please install the missing tools:"
        echo "- Terraform: https://www.terraform.io/downloads.html"
        echo "- kubectl: https://kubernetes.io/docs/tasks/tools/"
        echo "- Civo CLI: https://github.com/civo/cli"
        echo "- jq: https://stedolan.github.io/jq/"
        return 1
    fi
    
    # Check Civo authentication
    if ! civo apikey current >/dev/null 2>&1; then
        log_error "Civo CLI not authenticated. Run: civo apikey save <your-api-key>"
        return 1
    fi
    
    log_success "All prerequisites met"
    return 0
}

# Get Terraform directory
get_terraform_directory() {
    if [ "$DEPLOYMENT_TYPE" = "minimal" ]; then
        echo "civo-terraform-minimal"
    else
        echo "civo-terraform"
    fi
}

# Get Kubernetes directory
get_k8s_directory() {
    case $DEPLOYMENT_TYPE in
        minimal) echo "civo-k8s-minimal" ;;
        objectstore) echo "civo-k8s-objectstore" ;;
        *) echo "civo-k8s" ;;
    esac
}

# Deploy infrastructure
deploy_infrastructure() {
    if [ "$SKIP_TERRAFORM" = true ]; then
        log_warning "Skipping Terraform deployment"
        return 0
    fi
    
    local terraform_dir=$(get_terraform_directory)
    
    if [ ! -d "$terraform_dir" ]; then
        log_error "Terraform directory not found: $terraform_dir"
        return 1
    fi
    
    log_step "Deploying infrastructure with Terraform..."
    
    pushd "$terraform_dir" > /dev/null
    
    # Initialize Terraform
    log_step "Initializing Terraform..."
    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN: terraform init"
    else
        terraform init
    fi
    
    # Plan Terraform
    log_step "Planning Terraform deployment..."
    local plan_args=(
        "plan"
        "-var" "cluster_name=$CLUSTER_NAME"
        "-var" "civo_region=$CIVO_REGION" 
        "-var" "environment=$ENVIRONMENT"
    )
    
    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN: terraform ${plan_args[*]}"
    else
        terraform "${plan_args[@]}"
    fi
    
    # Apply Terraform
    if [ "$DRY_RUN" = false ]; then
        if [ "$FORCE" = true ] || { echo -n "Apply Terraform changes? (y/N): "; read -r response; [ "$response" = "y" ] || [ "$response" = "Y" ]; }; then
            log_step "Applying Terraform configuration..."
            terraform apply -auto-approve \
                -var "cluster_name=$CLUSTER_NAME" \
                -var "civo_region=$CIVO_REGION" \
                -var "environment=$ENVIRONMENT"
            
            log_success "Infrastructure deployed successfully"
        else
            log_warning "Terraform deployment skipped by user"
            popd > /dev/null
            return 1
        fi
    fi
    
    # Get outputs
    if [ "$DRY_RUN" = false ]; then
        log_step "Getting Terraform outputs..."
        terraform output -json > ../terraform-outputs.json
        
        # Save kubeconfig
        terraform output -raw kubeconfig > ../kubeconfig-civo.yaml
        
        log_success "Kubeconfig saved to kubeconfig-civo.yaml"
        echo "To use: export KUBECONFIG=\$(pwd)/kubeconfig-civo.yaml"
    fi
    
    popd > /dev/null
    return 0
}

# Deploy application
deploy_application() {
    if [ "$SKIP_K8S" = true ]; then
        log_warning "Skipping Kubernetes deployment"
        return 0
    fi
    
    local k8s_dir=$(get_k8s_directory)
    
    if [ ! -d "$k8s_dir" ]; then
        log_error "Kubernetes directory not found: $k8s_dir"
        return 1
    fi
    
    log_step "Deploying application to Kubernetes..."
    
    # Set kubeconfig
    if [ -f "kubeconfig-civo.yaml" ]; then
        export KUBECONFIG="$(pwd)/kubeconfig-civo.yaml"
        log_success "Using Civo kubeconfig"
    else
        log_warning "Civo kubeconfig not found, using default kubectl context"
    fi
    
    # Wait for cluster to be ready
    log_step "Waiting for cluster to be ready..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if [ "$DRY_RUN" = true ]; then
            echo "DRY RUN: kubectl get nodes"
            break
        else
            if kubectl get nodes --no-headers >/dev/null 2>&1; then
                log_success "Cluster is ready"
                break
            fi
        fi
        
        ((retries++))
        echo "Waiting for cluster... ($retries/$max_retries)"
        sleep 10
    done
    
    if [ $retries -eq $max_retries ] && [ "$DRY_RUN" = false ]; then
        log_error "Cluster not ready after $max_retries attempts"
        return 1
    fi
    
    # Create namespace
    log_step "Creating namespace..."
    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN: kubectl apply -f $k8s_dir/namespace.yaml"
    else
        kubectl apply -f "$k8s_dir/namespace.yaml"
    fi
    
    # Deploy configuration
    if [ -f "$k8s_dir/configmap.yaml" ]; then
        log_step "Deploying configuration..."
        if [ "$DRY_RUN" = true ]; then
            echo "DRY RUN: kubectl apply -f $k8s_dir/configmap.yaml"
        else
            kubectl apply -f "$k8s_dir/configmap.yaml"
        fi
    fi
    
    # Create secrets for object store (if needed)
    if [ "$DEPLOYMENT_TYPE" = "objectstore" ] && [ -f "terraform-outputs.json" ] && [ "$DRY_RUN" = false ]; then
        log_step "Creating object store credentials..."
        
        local access_key=$(jq -r '.object_store_credentials.value.access_key_id' terraform-outputs.json)
        local secret_key=$(jq -r '.object_store_credentials.value.secret_access_key' terraform-outputs.json)
        
        kubectl create secret generic civo-objectstore-credentials \
            --from-literal=ACCESS_KEY_ID="$access_key" \
            --from-literal=SECRET_ACCESS_KEY="$secret_key" \
            -n word-filter-app \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    # Deploy application
    log_step "Deploying application components..."
    
    for file in "$k8s_dir"/*.yaml; do
        local filename=$(basename "$file")
        if [ "$filename" != "namespace.yaml" ] && [ "$filename" != "configmap.yaml" ]; then
            echo "Deploying $filename..."
            if [ "$DRY_RUN" = true ]; then
                echo "DRY RUN: kubectl apply -f $file"
            else
                kubectl apply -f "$file"
            fi
        fi
    done
    
    log_success "Application deployed successfully"
    
    # Show status
    if [ "$DRY_RUN" = false ]; then
        log_step "Checking deployment status..."
        kubectl get pods -n word-filter-app
        kubectl get services -n word-filter-app
        
        # Get service URLs
        log_step "Getting service URLs..."
        local services=$(kubectl get services -n word-filter-app -o json)
        
        echo "$services" | jq -r '.items[] | select(.spec.type == "LoadBalancer") | "\(.metadata.name): http://\(.status.loadBalancer.ingress[0].ip // "pending")"'
        echo "$services" | jq -r '.items[] | select(.spec.type == "NodePort") | "\(.metadata.name): NodePort \(.spec.ports[0].nodePort)"'
    fi
    
    return 0
}

# Show summary
show_summary() {
    log_step "Deployment Summary"
    echo "=================="
    
    echo "Environment: $ENVIRONMENT"
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Cluster Name: $CLUSTER_NAME"
    echo "Civo Region: $CIVO_REGION"
    
    if [ -f "terraform-outputs.json" ] && [ "$DRY_RUN" = false ]; then
        echo ""
        echo "Infrastructure Details:"
        echo "- Cluster ID: $(jq -r '.cluster_id.value' terraform-outputs.json)"
        echo "- Master IP: $(jq -r '.master_ip.value' terraform-outputs.json)"
        echo "- API Endpoint: $(jq -r '.cluster_endpoint.value' terraform-outputs.json)"
        
        if jq -e '.estimated_monthly_cost' terraform-outputs.json > /dev/null; then
            local cost=$(jq -r '.estimated_monthly_cost.value.total' terraform-outputs.json)
            echo "- Estimated Cost: \$$cost/month"
        fi
    fi
    
    echo ""
    echo "Next Steps:"
    echo "1. Set kubeconfig: export KUBECONFIG=\$(pwd)/kubeconfig-civo.yaml"
    echo "2. Check pods: kubectl get pods -n word-filter-app"
    echo "3. Check services: kubectl get services -n word-filter-app"
    echo "4. View logs: kubectl logs -n word-filter-app -l app=word-filter-backend"
    
    if [ "$DEPLOYMENT_TYPE" = "minimal" ]; then
        echo "5. Port forward: kubectl port-forward -n word-filter-app service/word-filter-frontend 4201:80"
        echo "6. Port forward: kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001"
        echo "7. Access: http://localhost:4201"
    fi
}

# Main execution
main() {
    log_step "Starting Civo deployment for Word Filter App"
    echo "Environment: $ENVIRONMENT"
    echo "Deployment Type: $DEPLOYMENT_TYPE"
    echo "Cluster Name: $CLUSTER_NAME"
    echo "Civo Region: $CIVO_REGION"
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "Running in DRY RUN mode - no actual changes will be made"
    fi
    
    # Check prerequisites
    if ! test_prerequisites; then
        exit 1
    fi
    
    # Deploy infrastructure
    if ! deploy_infrastructure; then
        log_error "Infrastructure deployment failed"
        exit 1
    fi
    
    # Deploy application
    if ! deploy_application; then
        log_error "Application deployment failed"
        exit 1
    fi
    
    # Show summary
    show_summary
    
    log_success "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"
