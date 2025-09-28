# Terraform configuration for Civo Kubernetes cluster
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
  
  # Common tags for all resources
  common_labels = {
    "app"         = "word-filter"
    "managed-by"  = "terraform"
    "environment" = var.environment
  }
}

# Get available instance sizes
data "civo_size" "medium" {
  filter {
    key    = "name"
    values = [var.node_size]
  }

  sort {
    key       = "cpu"
    direction = "asc"
  }
}

# Create firewall for the cluster
resource "civo_firewall" "word_filter_fw" {
  name = "${local.cluster_name}-firewall"
  
  create_default_rules = true
  
  ingress_rule {
    label      = "kubernetes-api-server"
    protocol   = "tcp"
    port_range = "6443"
    cidr       = ["0.0.0.0/0"]
    action     = "allow"
  }
  
  ingress_rule {
    label      = "http"
    protocol   = "tcp"
    port_range = "80"
    cidr       = ["0.0.0.0/0"]
    action     = "allow"
  }
  
  ingress_rule {
    label      = "https"
    protocol   = "tcp"
    port_range = "443"
    cidr       = ["0.0.0.0/0"]
    action     = "allow"
  }
  
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

# Create Civo Kubernetes cluster
resource "civo_kubernetes_cluster" "word_filter_cluster" {
  name        = local.cluster_name
  firewall_id = civo_firewall.word_filter_fw.id
  
  # Pool configuration
  pools {
    label      = "${local.cluster_name}-workers"
    size       = var.node_size
    node_count = var.node_count
  }
  
  # Cluster configuration
  cluster_type = "k3s"  # Civo uses k3s by default
  kubernetes_version = var.kubernetes_version
  
  # Network configuration
  network_id = civo_network.word_filter_network.id
  
  # Applications to install (Civo Marketplace)
  applications = var.civo_applications
  
  tags = ["terraform", "word-filter", var.environment]
  
  # Wait for the cluster to be ready
  timeouts {
    create = "30m"
    delete = "15m"
  }
}

# Create a network for the cluster
resource "civo_network" "word_filter_network" {
  label  = "${local.cluster_name}-network"
  region = var.civo_region
}

# Create Object Store for word files (similar to S3)
resource "civo_object_store" "word_filter_storage" {
  name   = replace("${local.cluster_name}-storage", "_", "-")
  region = var.civo_region
  
  # Set max size (in GB) - Civo Object Store pricing
  max_size_gb = var.objectstore_max_size_gb
  
  access_key_id = var.objectstore_access_key
}

# Create Object Store credentials (similar to AWS IAM)
resource "civo_object_store_credential" "word_filter_credentials" {
  name               = "${local.cluster_name}-credentials"
  object_store_id    = civo_object_store.word_filter_storage.id
  access_key_id      = var.objectstore_access_key
  secret_access_key  = var.objectstore_secret_key
}

# Create volume for persistent storage (if needed)
resource "civo_volume" "word_filter_volume" {
  name      = "${local.cluster_name}-data"
  size_gb   = var.volume_size_gb
  
  # Attach to cluster region
  region = var.civo_region
}

# Load balancer for external access
resource "civo_loadbalancer" "word_filter_lb" {
  hostname                 = "${local.cluster_name}-lb"
  protocol                = "http"
  port                    = 80
  max_concurrent_requests = 10000
  policy                  = "round_robin"
  health_check_path       = "/health"
  fail_timeout            = 30
  max_conns               = 10
  ignore_invalid_backend_tls = true
  
  # Backend configuration will be managed by Kubernetes ingress
  backend {
    ip             = civo_kubernetes_cluster.word_filter_cluster.master_ip
    protocol       = "http"
    port           = 80
    max_conns      = 10
    max_fails      = 3
    fail_timeout   = 30
    weight         = 100
    check          = "fall=3 rise=2"
    check_interval = 10
  }
}

# DNS record for the application (optional)
resource "civo_dns_domain_record" "word_filter_dns" {
  count = var.domain_name != "" ? 1 : 0
  
  domain_id = var.dns_domain_id
  type      = "A"
  name      = var.subdomain
  value     = civo_loadbalancer.word_filter_lb.public_ip
  ttl       = 600
}

# Container registry for storing Docker images
# Note: Civo doesn't have a separate container registry service
# We'll use Docker Hub or external registry

# Database (if needed for future enhancements)
resource "civo_database" "word_filter_db" {
  count = var.enable_database ? 1 : 0
  
  name    = "${local.cluster_name}-db"
  size    = var.database_size
  version = var.database_version
  
  network_id = civo_network.word_filter_network.id
  firewall_id = civo_firewall.word_filter_fw.id
}

# Output important values
output "cluster_id" {
  description = "ID of the Civo Kubernetes cluster"
  value       = civo_kubernetes_cluster.word_filter_cluster.id
}

output "cluster_name" {
  description = "Name of the Civo Kubernetes cluster"
  value       = civo_kubernetes_cluster.word_filter_cluster.name
}

output "kubeconfig" {
  description = "Kubeconfig for the cluster"
  value       = civo_kubernetes_cluster.word_filter_cluster.kubeconfig
  sensitive   = true
}

output "cluster_endpoint" {
  description = "Endpoint for the Kubernetes API server"
  value       = civo_kubernetes_cluster.word_filter_cluster.api_endpoint
}

output "master_ip" {
  description = "IP address of the master node"
  value       = civo_kubernetes_cluster.word_filter_cluster.master_ip
}

output "object_store_endpoint" {
  description = "Civo Object Store endpoint"
  value       = civo_object_store.word_filter_storage.bucket_url
}

output "object_store_access_key" {
  description = "Object Store access key"
  value       = civo_object_store_credential.word_filter_credentials.access_key_id
  sensitive   = true
}

output "object_store_secret_key" {
  description = "Object Store secret key"
  value       = civo_object_store_credential.word_filter_credentials.secret_access_key
  sensitive   = true
}

output "load_balancer_ip" {
  description = "Public IP of the load balancer"
  value       = civo_loadbalancer.word_filter_lb.public_ip
}

output "network_id" {
  description = "ID of the network"
  value       = civo_network.word_filter_network.id
}

output "firewall_id" {
  description = "ID of the firewall"
  value       = civo_firewall.word_filter_fw.id
}

output "volume_id" {
  description = "ID of the persistent volume"
  value       = civo_volume.word_filter_volume.id
}

# If database is enabled, output its connection details
output "database_endpoint" {
  description = "Database endpoint (if enabled)"
  value       = var.enable_database ? civo_database.word_filter_db[0].endpoint : null
}

output "database_username" {
  description = "Database username (if enabled)"
  value       = var.enable_database ? civo_database.word_filter_db[0].username : null
}

output "database_password" {
  description = "Database password (if enabled)"
  value       = var.enable_database ? civo_database.word_filter_db[0].password : null
  sensitive   = true
}
