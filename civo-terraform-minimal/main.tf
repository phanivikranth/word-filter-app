# Minimal Terraform configuration for Civo Kubernetes cluster (Development/Testing)
terraform {
  required_version = ">= 1.0"
  required_providers {
    civo = {
      source  = "civo/civo"
      version = "~> 1.0"
    }
  }
}

# Configure the Civo Provider
provider "civo" {
  region = var.civo_region
}

# Local variables
locals {
  cluster_name = var.cluster_name
}

# Simple firewall - just the essentials
resource "civo_firewall" "minimal_fw" {
  name = "${local.cluster_name}-minimal-fw"
  
  # Create default rules (SSH, HTTP, HTTPS)
  create_default_rules = true
  
  # Just add our application ports
  ingress_rule {
    label      = "backend-api"
    protocol   = "tcp"
    port_range = "8001"
    cidr       = ["0.0.0.0/0"]
    action     = "allow"
  }
  
  ingress_rule {
    label      = "frontend-dev"
    protocol   = "tcp"
    port_range = "4200-4201"
    cidr       = ["0.0.0.0/0"]
    action     = "allow"
  }
}

# Minimal Civo Kubernetes cluster - single node for testing
resource "civo_kubernetes_cluster" "minimal_cluster" {
  name        = local.cluster_name
  firewall_id = civo_firewall.minimal_fw.id
  
  # Minimal pool - just 1 small node
  pools {
    label      = "${local.cluster_name}-node"
    size       = "g4s.kube.small"  # Cheapest option: 1 CPU, 2GB RAM - $10.37/month
    node_count = 1                 # Just 1 node for testing
  }
  
  # Basic cluster configuration
  cluster_type       = "k3s"
  kubernetes_version = var.kubernetes_version
  
  # Minimal applications - just what we need
  applications = [
    "Traefik2-nodeport",  # For ingress
    "metrics-server"      # For basic monitoring
  ]
  
  tags = ["terraform", "word-filter", "minimal", "testing"]
  
  # Reduced timeouts for faster testing
  timeouts {
    create = "15m"
    delete = "10m"
  }
}

# Simple Object Store for word files
resource "civo_object_store" "minimal_storage" {
  name   = "${local.cluster_name}-storage"
  region = var.civo_region
  
  # Minimal size for testing - 50GB
  max_size_gb = 50
  
  # Use provided credentials or generate them
  access_key_id = var.objectstore_access_key != "" ? var.objectstore_access_key : "wordfilter-${random_id.access_key.hex}"
}

# Generate random access key if not provided
resource "random_id" "access_key" {
  byte_length = 8
}

resource "random_password" "secret_key" {
  length  = 32
  special = false
}

# Object Store credentials
resource "civo_object_store_credential" "minimal_credentials" {
  name              = "${local.cluster_name}-creds"
  object_store_id   = civo_object_store.minimal_storage.id
  access_key_id     = civo_object_store.minimal_storage.access_key_id
  secret_access_key = var.objectstore_secret_key != "" ? var.objectstore_secret_key : random_password.secret_key.result
}

# No load balancer - use NodePort services for testing
# No DNS - use IP addresses
# No persistent volumes - use local storage
# No database - file-based storage only

# Output essential information
output "cluster_id" {
  description = "ID of the minimal Civo Kubernetes cluster"
  value       = civo_kubernetes_cluster.minimal_cluster.id
}

output "cluster_name" {
  description = "Name of the cluster"
  value       = civo_kubernetes_cluster.minimal_cluster.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = civo_kubernetes_cluster.minimal_cluster.api_endpoint
}

output "master_ip" {
  description = "IP address of the master node"
  value       = civo_kubernetes_cluster.minimal_cluster.master_ip
}

output "kubeconfig" {
  description = "Kubeconfig for kubectl access"
  value       = civo_kubernetes_cluster.minimal_cluster.kubeconfig
  sensitive   = true
}

output "object_store_endpoint" {
  description = "Object Store endpoint"
  value       = civo_object_store.minimal_storage.bucket_url
}

output "object_store_credentials" {
  description = "Object Store credentials"
  value = {
    access_key_id     = civo_object_store_credential.minimal_credentials.access_key_id
    secret_access_key = civo_object_store_credential.minimal_credentials.secret_access_key
  }
  sensitive = true
}

output "application_urls" {
  description = "URLs to access the application"
  value = {
    note         = "Use NodePort services - check with 'kubectl get services -n word-filter-app'"
    master_ip    = civo_kubernetes_cluster.minimal_cluster.master_ip
    backend_port = "NodePort will be assigned by Kubernetes (usually 30000-32767)"
    frontend_port = "NodePort will be assigned by Kubernetes (usually 30000-32767)"
  }
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost in USD"
  value = {
    cluster_node  = 10.37  # 1 small node
    object_store  = 1.00   # 50GB * $0.02
    total         = 11.37  # Very affordable for testing!
  }
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value = "echo '${base64decode(civo_kubernetes_cluster.minimal_cluster.kubeconfig)}' > kubeconfig-civo-minimal.yaml && export KUBECONFIG=$PWD/kubeconfig-civo-minimal.yaml"
}

output "next_steps" {
  description = "Next steps after deployment"
  value = [
    "# 1. Configure kubectl:",
    "echo '${base64decode(civo_kubernetes_cluster.minimal_cluster.kubeconfig)}' > kubeconfig-civo-minimal.yaml",
    "export KUBECONFIG=$PWD/kubeconfig-civo-minimal.yaml",
    "",
    "# 2. Wait for cluster to be ready:",
    "kubectl get nodes",
    "",
    "# 3. Deploy the application:",
    "kubectl apply -f ../civo-k8s-minimal/",
    "",
    "# 4. Get NodePort services:",
    "kubectl get services -n word-filter-app",
    "",
    "# 5. Access the application:",
    "echo 'Master IP: ${civo_kubernetes_cluster.minimal_cluster.master_ip}'",
    "echo 'Use kubectl port-forward for easy local access:'",
    "echo 'kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001'",
    "echo 'kubectl port-forward -n word-filter-app service/word-filter-frontend 4201:80'",
  ]
}
