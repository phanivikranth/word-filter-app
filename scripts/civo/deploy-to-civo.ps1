# PowerShell script to deploy Word Filter App to Civo Cloud
# Usage: .\deploy-to-civo.ps1 [-Environment prod|dev] [-SkipTerraform] [-SkipK8s] [-DeploymentType minimal|full|objectstore]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("prod", "dev", "staging")]
    [string]$Environment = "prod",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("minimal", "full", "objectstore")]
    [string]$DeploymentType = "full",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTerraform,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipK8s,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [string]$CivoRegion = "LON1",
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterName = "word-filter-civo",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Configuration
$ErrorActionPreference = "Stop"
$InformationPreference = "Continue"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$Cyan = "Cyan"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Step {
    param([string]$Message)
    Write-ColorOutput "🚀 $Message" $Blue
}

function Write-Success {
    param([string]$Message)
    Write-ColorOutput "✅ $Message" $Green
}

function Write-Warning {
    param([string]$Message)
    Write-ColorOutput "⚠️  $Message" $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-ColorOutput "❌ $Message" $Red
}

function Test-Command {
    param([string]$CommandName)
    return Get-Command $CommandName -ErrorAction SilentlyContinue
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."
    
    $missing = @()
    
    if (-not (Test-Command "terraform")) {
        $missing += "terraform"
    }
    
    if (-not (Test-Command "kubectl")) {
        $missing += "kubectl"
    }
    
    if (-not (Test-Command "civo")) {
        $missing += "civo CLI"
    }
    
    if ($missing.Count -gt 0) {
        Write-Error "Missing required tools: $($missing -join ', ')"
        Write-Host "Please install the missing tools:"
        Write-Host "- Terraform: https://www.terraform.io/downloads.html"
        Write-Host "- kubectl: https://kubernetes.io/docs/tasks/tools/"
        Write-Host "- Civo CLI: https://github.com/civo/cli"
        return $false
    }
    
    # Check Civo authentication
    try {
        civo apikey current | Out-Null
        Write-Success "Civo CLI authenticated"
    }
    catch {
        Write-Error "Civo CLI not authenticated. Run: civo apikey save <your-api-key>"
        return $false
    }
    
    Write-Success "All prerequisites met"
    return $true
}

function Get-TerraformDirectory {
    if ($DeploymentType -eq "minimal") {
        return "civo-terraform-minimal"
    }
    else {
        return "civo-terraform"
    }
}

function Get-K8sDirectory {
    switch ($DeploymentType) {
        "minimal" { return "civo-k8s-minimal" }
        "objectstore" { return "civo-k8s-objectstore" }
        default { return "civo-k8s" }
    }
}

function Deploy-Infrastructure {
    if ($SkipTerraform) {
        Write-Warning "Skipping Terraform deployment"
        return $true
    }
    
    $terraformDir = Get-TerraformDirectory
    
    if (-not (Test-Path $terraformDir)) {
        Write-Error "Terraform directory not found: $terraformDir"
        return $false
    }
    
    Write-Step "Deploying infrastructure with Terraform..."
    
    try {
        Push-Location $terraformDir
        
        # Initialize Terraform
        Write-Step "Initializing Terraform..."
        if ($DryRun) {
            Write-Host "DRY RUN: terraform init"
        }
        else {
            terraform init
            if ($LASTEXITCODE -ne 0) { throw "Terraform init failed" }
        }
        
        # Plan Terraform
        Write-Step "Planning Terraform deployment..."
        $planArgs = @(
            "plan"
            "-var", "cluster_name=$ClusterName"
            "-var", "civo_region=$CivoRegion"
            "-var", "environment=$Environment"
        )
        
        if ($DryRun) {
            Write-Host "DRY RUN: terraform $($planArgs -join ' ')"
        }
        else {
            & terraform @planArgs
            if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed" }
        }
        
        # Apply Terraform
        if (-not $DryRun) {
            if ($Force -or (Read-Host "Apply Terraform changes? (y/N)") -eq "y") {
                Write-Step "Applying Terraform configuration..."
                terraform apply -auto-approve -var "cluster_name=$ClusterName" -var "civo_region=$CivoRegion" -var "environment=$Environment"
                if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed" }
                
                Write-Success "Infrastructure deployed successfully"
            }
            else {
                Write-Warning "Terraform deployment skipped by user"
                return $false
            }
        }
        
        # Get outputs
        if (-not $DryRun) {
            Write-Step "Getting Terraform outputs..."
            $outputs = terraform output -json | ConvertFrom-Json
            
            # Save kubeconfig
            $kubeconfig = terraform output -raw kubeconfig
            $kubeconfig | Out-File -FilePath "kubeconfig-civo.yaml" -Encoding UTF8
            
            Write-Success "Kubeconfig saved to kubeconfig-civo.yaml"
            Write-Host "To use: `$env:KUBECONFIG = `"$(Get-Location)\kubeconfig-civo.yaml`""
            
            return $outputs
        }
        
        return $true
    }
    catch {
        Write-Error "Infrastructure deployment failed: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

function Deploy-Application {
    param($TerraformOutputs)
    
    if ($SkipK8s) {
        Write-Warning "Skipping Kubernetes deployment"
        return $true
    }
    
    $k8sDir = Get-K8sDirectory
    
    if (-not (Test-Path $k8sDir)) {
        Write-Error "Kubernetes directory not found: $k8sDir"
        return $false
    }
    
    Write-Step "Deploying application to Kubernetes..."
    
    try {
        # Set kubeconfig
        if (Test-Path "kubeconfig-civo.yaml") {
            $env:KUBECONFIG = "$(Get-Location)\kubeconfig-civo.yaml"
            Write-Success "Using Civo kubeconfig"
        }
        else {
            Write-Warning "Civo kubeconfig not found, using default kubectl context"
        }
        
        # Wait for cluster to be ready
        Write-Step "Waiting for cluster to be ready..."
        $retries = 0
        $maxRetries = 30
        
        while ($retries -lt $maxRetries) {
            try {
                if ($DryRun) {
                    Write-Host "DRY RUN: kubectl get nodes"
                    break
                }
                else {
                    $nodes = kubectl get nodes --no-headers 2>$null
                    if ($LASTEXITCODE -eq 0 -and $nodes) {
                        Write-Success "Cluster is ready"
                        break
                    }
                }
            }
            catch {
                # Ignore errors and retry
            }
            
            $retries++
            Write-Host "Waiting for cluster... ($retries/$maxRetries)"
            Start-Sleep 10
        }
        
        if ($retries -eq $maxRetries -and -not $DryRun) {
            Write-Error "Cluster not ready after $maxRetries attempts"
            return $false
        }
        
        # Create namespace
        Write-Step "Creating namespace..."
        if ($DryRun) {
            Write-Host "DRY RUN: kubectl apply -f $k8sDir/namespace.yaml"
        }
        else {
            kubectl apply -f "$k8sDir/namespace.yaml"
            if ($LASTEXITCODE -ne 0) { throw "Failed to create namespace" }
        }
        
        # Deploy configuration
        if (Test-Path "$k8sDir/configmap.yaml") {
            Write-Step "Deploying configuration..."
            if ($DryRun) {
                Write-Host "DRY RUN: kubectl apply -f $k8sDir/configmap.yaml"
            }
            else {
                kubectl apply -f "$k8sDir/configmap.yaml"
                if ($LASTEXITCODE -ne 0) { throw "Failed to deploy configuration" }
            }
        }
        
        # Create secrets for object store (if needed)
        if ($DeploymentType -eq "objectstore" -and $TerraformOutputs -and -not $DryRun) {
            Write-Step "Creating object store credentials..."
            
            $accessKey = $TerraformOutputs.object_store_credentials.value.access_key_id
            $secretKey = $TerraformOutputs.object_store_credentials.value.secret_access_key
            
            kubectl create secret generic civo-objectstore-credentials `
                --from-literal=ACCESS_KEY_ID="$accessKey" `
                --from-literal=SECRET_ACCESS_KEY="$secretKey" `
                -n word-filter-app `
                --dry-run=client -o yaml | kubectl apply -f -
        }
        
        # Deploy application
        Write-Step "Deploying application components..."
        $deploymentFiles = Get-ChildItem -Path $k8sDir -Filter "*.yaml" | Where-Object { $_.Name -ne "namespace.yaml" -and $_.Name -ne "configmap.yaml" }
        
        foreach ($file in $deploymentFiles) {
            Write-Host "Deploying $($file.Name)..."
            if ($DryRun) {
                Write-Host "DRY RUN: kubectl apply -f $($file.FullName)"
            }
            else {
                kubectl apply -f $file.FullName
                if ($LASTEXITCODE -ne 0) { throw "Failed to deploy $($file.Name)" }
            }
        }
        
        Write-Success "Application deployed successfully"
        
        # Show status
        if (-not $DryRun) {
            Write-Step "Checking deployment status..."
            kubectl get pods -n word-filter-app
            kubectl get services -n word-filter-app
            
            # Get service URLs
            Write-Step "Getting service URLs..."
            $services = kubectl get services -n word-filter-app -o json | ConvertFrom-Json
            
            foreach ($service in $services.items) {
                if ($service.spec.type -eq "LoadBalancer") {
                    $name = $service.metadata.name
                    $ip = $service.status.loadBalancer.ingress[0].ip
                    if ($ip) {
                        Write-Success "$name: http://$ip"
                    }
                    else {
                        Write-Warning "$name: LoadBalancer IP pending..."
                    }
                }
                elseif ($service.spec.type -eq "NodePort") {
                    $name = $service.metadata.name
                    $nodePort = $service.spec.ports[0].nodePort
                    $nodeIP = kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}'
                    if (-not $nodeIP) {
                        $nodeIP = kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}'
                    }
                    Write-Success "$name: http://${nodeIP}:$nodePort"
                }
            }
        }
        
        return $true
    }
    catch {
        Write-Error "Application deployment failed: $_"
        return $false
    }
}

function Show-Summary {
    param($TerraformOutputs)
    
    Write-Step "Deployment Summary"
    Write-Host "=================="
    
    Write-Host "Environment: $Environment"
    Write-Host "Deployment Type: $DeploymentType"
    Write-Host "Cluster Name: $ClusterName"
    Write-Host "Civo Region: $CivoRegion"
    
    if ($TerraformOutputs -and -not $DryRun) {
        Write-Host ""
        Write-Host "Infrastructure Details:"
        Write-Host "- Cluster ID: $($TerraformOutputs.cluster_id.value)"
        Write-Host "- Master IP: $($TerraformOutputs.master_ip.value)"
        Write-Host "- API Endpoint: $($TerraformOutputs.cluster_endpoint.value)"
        
        if ($TerraformOutputs.estimated_monthly_cost) {
            $cost = $TerraformOutputs.estimated_monthly_cost.value
            Write-Host "- Estimated Cost: `$$($cost.total)/month"
        }
    }
    
    Write-Host ""
    Write-Host "Next Steps:"
    Write-Host "1. Set kubeconfig: `$env:KUBECONFIG = `"kubeconfig-civo.yaml`""
    Write-Host "2. Check pods: kubectl get pods -n word-filter-app"
    Write-Host "3. Check services: kubectl get services -n word-filter-app"
    Write-Host "4. View logs: kubectl logs -n word-filter-app -l app=word-filter-backend"
    
    if ($DeploymentType -eq "minimal") {
        Write-Host "5. Port forward: kubectl port-forward -n word-filter-app service/word-filter-frontend 4201:80"
        Write-Host "6. Port forward: kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001"
        Write-Host "7. Access: http://localhost:4201"
    }
}

# Main execution
function Main {
    Write-Step "Starting Civo deployment for Word Filter App"
    Write-Host "Environment: $Environment"
    Write-Host "Deployment Type: $DeploymentType"
    Write-Host "Cluster Name: $ClusterName"
    Write-Host "Civo Region: $CivoRegion"
    
    if ($DryRun) {
        Write-Warning "Running in DRY RUN mode - no actual changes will be made"
    }
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    # Deploy infrastructure
    $terraformOutputs = Deploy-Infrastructure
    if (-not $terraformOutputs) {
        Write-Error "Infrastructure deployment failed"
        exit 1
    }
    
    # Deploy application
    if (-not (Deploy-Application -TerraformOutputs $terraformOutputs)) {
        Write-Error "Application deployment failed"
        exit 1
    }
    
    # Show summary
    Show-Summary -TerraformOutputs $terraformOutputs
    
    Write-Success "🎉 Deployment completed successfully!"
}

# Run main function
try {
    Main
}
catch {
    Write-Error "Deployment failed: $_"
    exit 1
}
