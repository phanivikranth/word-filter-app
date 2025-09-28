# Civo Infrastructure Variables

# Basic Configuration
variable "civo_region" {
  description = "Civo region for resources"
  type        = string
  default     = "LON1"  # London region (cheapest)
  
  validation {
    condition = contains([
      "LON1",   # London, UK
      "NYC1",   # New York, US
      "FRA1"    # Frankfurt, Germany
    ], var.civo_region)
    error_message = "Civo region must be one of: LON1, NYC1, FRA1"
  }
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "word-filter-cluster"
  
  validation {
    condition     = length(var.cluster_name) <= 32 && can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must be 32 characters or less and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Kubernetes Configuration
variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28.2-k3s1"  # Civo uses k3s
}

variable "node_size" {
  description = "Size of the worker nodes"
  type        = string
  default     = "g4s.kube.medium"  # 2 CPU, 4GB RAM, 40GB SSD
  
  validation {
    condition = contains([
      "g4s.kube.small",    # 1 CPU, 2GB RAM, 25GB SSD - $10.37/month
      "g4s.kube.medium",   # 2 CPU, 4GB RAM, 40GB SSD - $20.73/month  
      "g4s.kube.large",    # 4 CPU, 8GB RAM, 80GB SSD - $41.46/month
      "g4s.kube.xlarge"    # 6 CPU, 16GB RAM, 160GB SSD - $82.92/month
    ], var.node_size)
    error_message = "Node size must be one of: g4s.kube.small, g4s.kube.medium, g4s.kube.large, g4s.kube.xlarge"
  }
}

variable "node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
  
  validation {
    condition     = var.node_count >= 1 && var.node_count <= 10
    error_message = "Node count must be between 1 and 10."
  }
}

# Civo Applications (Marketplace)
variable "civo_applications" {
  description = "List of Civo marketplace applications to install"
  type        = list(string)
  default = [
    "Traefik2-nodeport",     # Load balancer/ingress controller
    "metrics-server",        # For HPA and resource monitoring
    "cert-manager",          # For SSL/TLS certificates
    "longhorn"               # For persistent storage
  ]
}

# Object Store Configuration (Civo's S3-compatible storage)
variable "objectstore_max_size_gb" {
  description = "Maximum size of object store in GB"
  type        = number
  default     = 500
  
  validation {
    condition     = var.objectstore_max_size_gb >= 1 && var.objectstore_max_size_gb <= 10000
    error_message = "Object store size must be between 1 and 10000 GB."
  }
}

variable "objectstore_access_key" {
  description = "Object store access key ID"
  type        = string
  default     = ""
}

variable "objectstore_secret_key" {
  description = "Object store secret access key"
  type        = string
  sensitive   = true
  default     = ""
}

# Volume Configuration
variable "volume_size_gb" {
  description = "Size of the persistent volume in GB"
  type        = number
  default     = 20
  
  validation {
    condition     = var.volume_size_gb >= 1 && var.volume_size_gb <= 2000
    error_message = "Volume size must be between 1 and 2000 GB."
  }
}

# DNS Configuration
variable "domain_name" {
  description = "Domain name for the application (empty to skip DNS)"
  type        = string
  default     = ""
}

variable "subdomain" {
  description = "Subdomain for the application"
  type        = string
  default     = "word-filter"
}

variable "dns_domain_id" {
  description = "Civo DNS domain ID (required if domain_name is set)"
  type        = string
  default     = ""
}

# Database Configuration (optional)
variable "enable_database" {
  description = "Enable managed database"
  type        = bool
  default     = false
}

variable "database_size" {
  description = "Database instance size"
  type        = string
  default     = "g4s.db.small"
  
  validation {
    condition = contains([
      "g4s.db.small",   # 1 CPU, 2GB RAM, 25GB SSD - $15/month
      "g4s.db.medium",  # 2 CPU, 4GB RAM, 50GB SSD - $30/month
      "g4s.db.large"    # 4 CPU, 8GB RAM, 100GB SSD - $60/month
    ], var.database_size)
    error_message = "Database size must be one of: g4s.db.small, g4s.db.medium, g4s.db.large"
  }
}

variable "database_version" {
  description = "Database version (PostgreSQL)"
  type        = string
  default     = "13"
  
  validation {
    condition = contains([
      "11", "12", "13", "14", "15"
    ], var.database_version)
    error_message = "Database version must be one of: 11, 12, 13, 14, 15"
  }
}

# Cost optimization
variable "enable_spot_instances" {
  description = "Use spot instances for cost savings (not directly available in Civo)"
  type        = bool
  default     = false
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    "Project"     = "WordFilterApp"
    "ManagedBy"   = "Terraform"
    "Provider"    = "Civo"
  }
}

# Container Registry Configuration
variable "container_registry" {
  description = "Container registry to use (Docker Hub, GitHub Container Registry, etc.)"
  type        = string
  default     = "docker.io"
}

variable "container_registry_username" {
  description = "Container registry username"
  type        = string
  default     = ""
}

variable "container_registry_token" {
  description = "Container registry access token"
  type        = string
  sensitive   = true
  default     = ""
}

# Application Configuration
variable "backend_image" {
  description = "Backend container image"
  type        = string
  default     = "phanivikranth/word-filter-backend:latest"
}

variable "frontend_image" {
  description = "Frontend container image"
  type        = string
  default     = "phanivikranth/word-filter-frontend:latest"
}

variable "backend_replicas" {
  description = "Number of backend replicas"
  type        = number
  default     = 3
  
  validation {
    condition     = var.backend_replicas >= 1 && var.backend_replicas <= 10
    error_message = "Backend replicas must be between 1 and 10."
  }
}

variable "frontend_replicas" {
  description = "Number of frontend replicas"
  type        = number
  default     = 2
  
  validation {
    condition     = var.frontend_replicas >= 1 && var.frontend_replicas <= 10
    error_message = "Frontend replicas must be between 1 and 10."
  }
}

# Monitoring and Logging
variable "enable_monitoring" {
  description = "Enable Prometheus and Grafana monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable centralized logging with Loki"
  type        = bool
  default     = true
}

# Security
variable "enable_network_policies" {
  description = "Enable Kubernetes network policies"
  type        = bool
  default     = true
}

variable "enable_pod_security_policies" {
  description = "Enable pod security policies"
  type        = bool
  default     = true
}

# Backup Configuration
variable "enable_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
  
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention must be between 1 and 365 days."
  }
}
