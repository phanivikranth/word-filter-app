# Word Filter App - Build and Deploy PowerShell Script
# This script builds Docker images, pushes to AWS ECR, and deploys to EKS

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("build", "push", "deploy", "status")]
    [string]$Action = "deploy"
)

# Configuration
$AWS_REGION = "us-west-2"
$ECR_REGISTRY = "your-account.dkr.ecr.$AWS_REGION.amazonaws.com"
$APP_NAME = "word-filter"
$NAMESPACE = "word-filter-app"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    try {
        docker --version | Out-Null
    } catch {
        Write-Error "Docker is not installed or not in PATH"
        exit 1
    }
    
    # Check AWS CLI
    try {
        aws --version | Out-Null
    } catch {
        Write-Error "AWS CLI is not installed or not in PATH"
        exit 1
    }
    
    # Check kubectl
    try {
        kubectl version --client | Out-Null
    } catch {
        Write-Error "kubectl is not installed or not in PATH"
        exit 1
    }
    
    # Check AWS credentials
    try {
        aws sts get-caller-identity | Out-Null
    } catch {
        Write-Error "AWS credentials not configured"
        exit 1
    }
    
    Write-Success "All prerequisites met"
}

function New-ECRRepositories {
    Write-Info "Creating ECR repositories..."
    
    # Create backend repository
    try {
        aws ecr describe-repositories --repository-names "$APP_NAME-backend" --region $AWS_REGION 2>$null | Out-Null
    } catch {
        Write-Info "Creating backend ECR repository..."
        aws ecr create-repository --repository-name "$APP_NAME-backend" --region $AWS_REGION
    }
    
    # Create frontend repository
    try {
        aws ecr describe-repositories --repository-names "$APP_NAME-frontend" --region $AWS_REGION 2>$null | Out-Null
    } catch {
        Write-Info "Creating frontend ECR repository..."
        aws ecr create-repository --repository-name "$APP_NAME-frontend" --region $AWS_REGION
    }
    
    Write-Success "ECR repositories ready"
}

function Build-Images {
    Write-Info "Building Docker images..."
    
    # Login to ECR
    Write-Info "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build backend image
    Write-Info "Building backend image..."
    Set-Location backend
    docker build -t "$ECR_REGISTRY/$APP_NAME-backend:latest" .
    Set-Location ..
    
    # Build frontend image
    Write-Info "Building frontend image..."
    Set-Location frontend
    docker build -t "$ECR_REGISTRY/$APP_NAME-frontend:latest" .
    Set-Location ..
    
    Write-Success "Docker images built successfully"
}

function Push-Images {
    Write-Info "Pushing images to ECR..."
    
    docker push "$ECR_REGISTRY/$APP_NAME-backend:latest"
    docker push "$ECR_REGISTRY/$APP_NAME-frontend:latest"
    
    Write-Success "Images pushed to ECR"
}

function Deploy-ToKubernetes {
    Write-Info "Deploying to Kubernetes..."
    
    # Update kubeconfig
    Write-Info "Updating kubeconfig..."
    aws eks update-kubeconfig --region $AWS_REGION --name word-filter-cluster
    
    # Create namespace
    Write-Info "Creating namespace..."
    kubectl apply -f k8s/namespace.yaml
    
    # Update image references in deployment files
    Write-Info "Updating image references..."
    (Get-Content k8s/backend-deployment.yaml) -replace 'your-account.dkr.ecr.us-west-2.amazonaws.com', $ECR_REGISTRY | Set-Content k8s/backend-deployment.yaml.tmp
    Move-Item k8s/backend-deployment.yaml.tmp k8s/backend-deployment.yaml
    
    (Get-Content k8s/frontend-deployment.yaml) -replace 'your-account.dkr.ecr.us-west-2.amazonaws.com', $ECR_REGISTRY | Set-Content k8s/frontend-deployment.yaml.tmp
    Move-Item k8s/frontend-deployment.yaml.tmp k8s/frontend-deployment.yaml
    
    # Apply Kubernetes manifests
    Write-Info "Applying backend deployment..."
    kubectl apply -f k8s/backend-deployment.yaml
    
    Write-Info "Applying frontend deployment..."
    kubectl apply -f k8s/frontend-deployment.yaml
    
    Write-Info "Applying ingress..."
    kubectl apply -f k8s/ingress.yaml
    
    # Wait for deployments
    Write-Info "Waiting for backend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-backend -n $NAMESPACE
    
    Write-Info "Waiting for frontend deployment..."
    kubectl wait --for=condition=available --timeout=600s deployment/word-filter-frontend -n $NAMESPACE
    
    Write-Success "Deployment completed successfully"
}

function Show-Status {
    Write-Info "Deployment Status:"
    
    Write-Host ""
    Write-Host "Pods:"
    kubectl get pods -n $NAMESPACE
    
    Write-Host ""
    Write-Host "Services:"
    kubectl get services -n $NAMESPACE
    
    Write-Host ""
    Write-Host "Ingress:"
    kubectl get ingress -n $NAMESPACE
    
    Write-Host ""
    Write-Info "To get the external IP address:"
    Write-Host "kubectl get ingress word-filter-ingress -n $NAMESPACE"
    
    Write-Host ""
    Write-Info "To check logs:"
    Write-Host "kubectl logs -f deployment/word-filter-backend -n $NAMESPACE"
    Write-Host "kubectl logs -f deployment/word-filter-frontend -n $NAMESPACE"
}

function Invoke-FullDeployment {
    Write-Info "Starting Word Filter App deployment..."
    
    Test-Prerequisites
    New-ECRRepositories
    Build-Images
    Push-Images
    Deploy-ToKubernetes
    Show-Status
    
    Write-Success "Deployment pipeline completed!"
    Write-Info "Your app should be accessible via the ingress URL once DNS propagates"
}

# Main execution
switch ($Action) {
    "build" {
        Write-Info "Building images only..."
        Test-Prerequisites
        Build-Images
    }
    "push" {
        Write-Info "Pushing images only..."
        Test-Prerequisites
        Push-Images
    }
    "deploy" {
        Invoke-FullDeployment
    }
    "status" {
        Show-Status
    }
}
