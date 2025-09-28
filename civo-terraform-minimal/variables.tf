# Minimal Civo Infrastructure Variables (Development/Testing)

variable "civo_region" {
  description = "Civo region for resources"
  type        = string
  default     = "LON1"  # London region - cheapest option
  
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
  default     = "word-filter-minimal"
  
  validation {
    condition     = length(var.cluster_name) <= 32 && can(regex("^[a-z0-9-]+$", var.cluster_name))
    error_message = "Cluster name must be 32 characters or less and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version (k3s)"
  type        = string
  default     = "1.28.2-k3s1"
}

variable "objectstore_access_key" {
  description = "Object store access key ID (leave empty to auto-generate)"
  type        = string
  default     = ""
}

variable "objectstore_secret_key" {
  description = "Object store secret access key (leave empty to auto-generate)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    "Project"     = "WordFilterApp"
    "Environment" = "development"
    "Purpose"     = "testing"
    "ManagedBy"   = "Terraform"
    "Provider"    = "Civo"
    "CostProfile" = "minimal"
  }
}
