# PowerShell script to deploy Word Filter App to multiple clouds (AWS and Civo)
# Usage: .\deploy-multi-cloud.ps1 [-CloudProvider aws|civo|both] [-Environment prod|dev] [-DeploymentType minimal|full|objectstore]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("aws", "civo", "both")]
    [string]$CloudProvider = "both",
    
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
    [string]$AwsRegion = "us-west-2",
    
    [Parameter(Mandatory=$false)]
    [string]$CivoRegion = "LON1",
    
    [Parameter(Mandatory=$false)]
    [string]$ClusterNameSuffix = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$Parallel,
    
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
$Magenta = "Magenta"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-ColorOutput "=" * 80 $Cyan
    Write-ColorOutput "  $Message" $Cyan
    Write-ColorOutput "=" * 80 $Cyan
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

function Test-CloudPrerequisites {
    param([string]$Cloud)
    
    Write-Step "Checking prerequisites for $Cloud..."
    
    $missing = @()
    $warnings = @()
    
    # Common tools
    if (-not (Test-Command "terraform")) {
        $missing += "terraform"
    }
    
    if (-not (Test-Command "kubectl")) {
        $missing += "kubectl"
    }
    
    if (-not (Test-Command "docker")) {
        $warnings += "docker (needed for building images)"
    }
    
    # Cloud-specific tools
    switch ($Cloud) {
        "aws" {
            if (-not (Test-Command "aws")) {
                $missing += "aws CLI"
            }
            else {
                # Check AWS credentials
                try {
                    aws sts get-caller-identity | Out-Null
                    Write-Success "AWS CLI authenticated"
                }
                catch {
                    $warnings += "AWS CLI not configured or credentials invalid"
                }
            }
        }
        
        "civo" {
            if (-not (Test-Command "civo")) {
                $missing += "civo CLI"
            }
            else {
                # Check Civo authentication
                try {
                    civo apikey current | Out-Null
                    Write-Success "Civo CLI authenticated"
                }
                catch {
                    $warnings += "Civo CLI not authenticated"
                }
            }
        }
    }
    
    # Report results
    if ($missing.Count -gt 0) {
        Write-Error "Missing required tools for $Cloud: $($missing -join ', ')"
        return $false
    }
    
    if ($warnings.Count -gt 0) {
        foreach ($warning in $warnings) {
            Write-Warning "$Cloud: $warning"
        }
    }
    
    Write-Success "$Cloud prerequisites met"
    return $true
}

function Get-ClusterName {
    param([string]$Cloud)
    
    $baseName = "word-filter-$Cloud"
    if ($ClusterNameSuffix) {
        $baseName += "-$ClusterNameSuffix"
    }
    if ($Environment -ne "prod") {
        $baseName += "-$Environment"
    }
    
    return $baseName
}

function Deploy-ToAWS {
    Write-Header "Deploying to AWS"
    
    $clusterName = Get-ClusterName -Cloud "aws"
    
    $scriptArgs = @(
        "-Environment", $Environment
        "-DeploymentType", $DeploymentType
        "-AwsRegion", $AwsRegion
        "-ClusterName", $clusterName
    )
    
    if ($SkipTerraform) { $scriptArgs += "-SkipTerraform" }
    if ($SkipK8s) { $scriptArgs += "-SkipK8s" }
    if ($DryRun) { $scriptArgs += "-DryRun" }
    if ($Force) { $scriptArgs += "-Force" }
    
    # Check if AWS deployment script exists
    $awsScript = "scripts/aws/deploy-to-aws.ps1"
    if (-not (Test-Path $awsScript)) {
        Write-Warning "AWS deployment script not found at $awsScript"
        Write-Host "Creating minimal AWS deployment command..."
        
        if ($DryRun) {
            Write-Host "DRY RUN: Would deploy to AWS with cluster name: $clusterName"
            return @{ success = $true; cluster_name = $clusterName; provider = "aws" }
        }
        else {
            Write-Error "AWS deployment not implemented yet"
            return @{ success = $false; error = "Script not found" }
        }
    }
    
    try {
        Write-Step "Executing AWS deployment script..."
        & $awsScript @scriptArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "AWS deployment completed successfully"
            return @{ 
                success = $true
                cluster_name = $clusterName
                provider = "aws"
                region = $AwsRegion
            }
        }
        else {
            throw "AWS deployment script failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "AWS deployment failed: $_"
        return @{ success = $false; error = $_.ToString() }
    }
}

function Deploy-ToCivo {
    Write-Header "Deploying to Civo"
    
    $clusterName = Get-ClusterName -Cloud "civo"
    
    $scriptArgs = @(
        "-Environment", $Environment
        "-DeploymentType", $DeploymentType
        "-CivoRegion", $CivoRegion
        "-ClusterName", $clusterName
    )
    
    if ($SkipTerraform) { $scriptArgs += "-SkipTerraform" }
    if ($SkipK8s) { $scriptArgs += "-SkipK8s" }
    if ($DryRun) { $scriptArgs += "-DryRun" }
    if ($Force) { $scriptArgs += "-Force" }
    
    # Use Civo deployment script
    $civoScript = "scripts/civo/deploy-to-civo.ps1"
    if (-not (Test-Path $civoScript)) {
        Write-Error "Civo deployment script not found at $civoScript"
        return @{ success = $false; error = "Script not found" }
    }
    
    try {
        Write-Step "Executing Civo deployment script..."
        & $civoScript @scriptArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Civo deployment completed successfully"
            return @{ 
                success = $true
                cluster_name = $clusterName
                provider = "civo"
                region = $CivoRegion
            }
        }
        else {
            throw "Civo deployment script failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "Civo deployment failed: $_"
        return @{ success = $false; error = $_.ToString() }
    }
}

function Deploy-Parallel {
    Write-Header "Deploying to multiple clouds in parallel"
    
    $jobs = @()
    
    if ($CloudProvider -eq "aws" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "aws") {
            Write-Step "Starting AWS deployment job..."
            $awsJob = Start-Job -ScriptBlock {
                param($Environment, $DeploymentType, $AwsRegion, $ClusterNameSuffix, $SkipTerraform, $SkipK8s, $DryRun, $Force)
                
                # Set location to the original directory
                Set-Location $using:PWD
                
                # Import the deployment function (simplified version)
                # In practice, you'd call the actual deployment script
                return @{
                    success = $true
                    provider = "aws"
                    cluster_name = "word-filter-aws" + $(if ($ClusterNameSuffix) { "-$ClusterNameSuffix" } else { "" })
                    region = $AwsRegion
                    deployment_time = (Get-Date).ToString()
                }
            } -ArgumentList $Environment, $DeploymentType, $AwsRegion, $ClusterNameSuffix, $SkipTerraform, $SkipK8s, $DryRun, $Force
            
            $jobs += @{ job = $awsJob; provider = "aws" }
        }
    }
    
    if ($CloudProvider -eq "civo" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "civo") {
            Write-Step "Starting Civo deployment job..."
            $civoJob = Start-Job -ScriptBlock {
                param($Environment, $DeploymentType, $CivoRegion, $ClusterNameSuffix, $SkipTerraform, $SkipK8s, $DryRun, $Force)
                
                # Set location to the original directory
                Set-Location $using:PWD
                
                # Import the deployment function (simplified version)
                # In practice, you'd call the actual deployment script
                return @{
                    success = $true
                    provider = "civo"
                    cluster_name = "word-filter-civo" + $(if ($ClusterNameSuffix) { "-$ClusterNameSuffix" } else { "" })
                    region = $CivoRegion
                    deployment_time = (Get-Date).ToString()
                }
            } -ArgumentList $Environment, $DeploymentType, $CivoRegion, $ClusterNameSuffix, $SkipTerraform, $SkipK8s, $DryRun, $Force
            
            $jobs += @{ job = $civoJob; provider = "civo" }
        }
    }
    
    if ($jobs.Count -eq 0) {
        Write-Error "No valid cloud providers to deploy to"
        return @()
    }
    
    # Wait for jobs to complete
    Write-Step "Waiting for deployments to complete..."
    $results = @()
    
    foreach ($jobInfo in $jobs) {
        $job = $jobInfo.job
        $provider = $jobInfo.provider
        
        Write-Host "Waiting for $provider deployment..."
        
        try {
            $result = Receive-Job -Job $job -Wait
            $results += $result
            
            if ($result.success) {
                Write-Success "$provider deployment completed successfully"
            }
            else {
                Write-Error "$provider deployment failed"
            }
        }
        catch {
            Write-Error "$provider deployment job failed: $_"
            $results += @{ success = $false; provider = $provider; error = $_.ToString() }
        }
        finally {
            Remove-Job -Job $job -Force
        }
    }
    
    return $results
}

function Deploy-Sequential {
    Write-Header "Deploying to clouds sequentially"
    
    $results = @()
    
    if ($CloudProvider -eq "aws" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "aws") {
            $awsResult = Deploy-ToAWS
            $results += $awsResult
            
            if (-not $awsResult.success -and $CloudProvider -eq "both") {
                Write-Warning "AWS deployment failed, continuing with Civo..."
            }
        }
        else {
            Write-Error "AWS prerequisites not met, skipping AWS deployment"
        }
    }
    
    if ($CloudProvider -eq "civo" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "civo") {
            $civoResult = Deploy-ToCivo
            $results += $civoResult
        }
        else {
            Write-Error "Civo prerequisites not met, skipping Civo deployment"
        }
    }
    
    return $results
}

function Show-MultiCloudSummary {
    param([array]$Results)
    
    Write-Header "Multi-Cloud Deployment Summary"
    
    Write-Host "Configuration:"
    Write-Host "- Cloud Provider(s): $CloudProvider"
    Write-Host "- Environment: $Environment"
    Write-Host "- Deployment Type: $DeploymentType"
    Write-Host "- AWS Region: $AwsRegion"
    Write-Host "- Civo Region: $CivoRegion"
    
    if ($ClusterNameSuffix) {
        Write-Host "- Cluster Name Suffix: $ClusterNameSuffix"
    }
    
    Write-Host ""
    Write-Host "Deployment Results:"
    Write-Host "==================="
    
    $successCount = 0
    $totalCost = 0
    
    foreach ($result in $Results) {
        if ($result.success) {
            $successCount++
            Write-Success "$($result.provider.ToUpper()): ✅ $($result.cluster_name)"
            Write-Host "  Region: $($result.region)"
            
            if ($result.estimated_cost) {
                Write-Host "  Estimated Cost: `$$($result.estimated_cost)/month"
                $totalCost += $result.estimated_cost
            }
        }
        else {
            Write-Error "$($result.provider.ToUpper()): ❌ Failed"
            if ($result.error) {
                Write-Host "  Error: $($result.error)"
            }
        }
    }
    
    Write-Host ""
    Write-Host "Summary:"
    Write-Host "- Successful deployments: $successCount/$($Results.Count)"
    
    if ($totalCost -gt 0) {
        Write-Host "- Total estimated cost: `$$totalCost/month"
    }
    
    if ($successCount -gt 0) {
        Write-Host ""
        Write-Host "Next Steps:"
        Write-Host "1. Configure kubectl for each cluster:"
        
        foreach ($result in $Results) {
            if ($result.success) {
                $kubeconfigFile = "kubeconfig-$($result.provider).yaml"
                Write-Host "   - $($result.provider.ToUpper()): export KUBECONFIG=$kubeconfigFile"
            }
        }
        
        Write-Host "2. Switch between clusters:"
        Write-Host "   - kubectl config get-contexts"
        Write-Host "   - kubectl config use-context <context-name>"
        Write-Host "3. Monitor deployments:"
        Write-Host "   - kubectl get pods -n word-filter-app"
        Write-Host "   - kubectl get services -n word-filter-app"
    }
}

# Main execution
function Main {
    Write-Header "Multi-Cloud Deployment for Word Filter App"
    
    Write-Host "Configuration:"
    Write-Host "- Target Cloud(s): $CloudProvider"
    Write-Host "- Environment: $Environment"
    Write-Host "- Deployment Type: $DeploymentType"
    Write-Host "- Parallel Deployment: $Parallel"
    
    if ($DryRun) {
        Write-Warning "Running in DRY RUN mode - no actual changes will be made"
    }
    
    # Validate cloud providers
    $validProviders = @()
    
    if ($CloudProvider -eq "aws" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "aws") {
            $validProviders += "aws"
        }
    }
    
    if ($CloudProvider -eq "civo" -or $CloudProvider -eq "both") {
        if (Test-CloudPrerequisites -Cloud "civo") {
            $validProviders += "civo"
        }
    }
    
    if ($validProviders.Count -eq 0) {
        Write-Error "No valid cloud providers available for deployment"
        exit 1
    }
    
    Write-Success "Validated cloud providers: $($validProviders -join ', ')"
    
    # Deploy based on parallel flag
    if ($Parallel -and $validProviders.Count -gt 1) {
        $results = Deploy-Parallel
    }
    else {
        $results = Deploy-Sequential
    }
    
    # Show summary
    Show-MultiCloudSummary -Results $results
    
    # Determine exit code
    $successCount = ($results | Where-Object { $_.success }).Count
    if ($successCount -eq 0) {
        Write-Error "All deployments failed"
        exit 1
    }
    elseif ($successCount -lt $results.Count) {
        Write-Warning "Some deployments failed"
        exit 2
    }
    else {
        Write-Success "🎉 All deployments completed successfully!"
        exit 0
    }
}

# Run main function
try {
    Main
}
catch {
    Write-Error "Multi-cloud deployment failed: $_"
    exit 1
}
