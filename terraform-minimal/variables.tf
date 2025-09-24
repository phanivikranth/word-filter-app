# Minimal variables for testing setup

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "word-filter-test"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project     = "word-filter-app"
    Environment = "testing"
    ManagedBy   = "terraform"
    Purpose     = "minimal-testing"
  }
}
