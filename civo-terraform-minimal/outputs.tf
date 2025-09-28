# Minimal Civo Infrastructure Outputs

output "cluster_details" {
  description = "Essential cluster information"
  value = {
    id                = civo_kubernetes_cluster.minimal_cluster.id
    name              = civo_kubernetes_cluster.minimal_cluster.name
    api_endpoint      = civo_kubernetes_cluster.minimal_cluster.api_endpoint
    master_ip         = civo_kubernetes_cluster.minimal_cluster.master_ip
    kubernetes_version = civo_kubernetes_cluster.minimal_cluster.kubernetes_version
    status            = civo_kubernetes_cluster.minimal_cluster.status
    ready             = civo_kubernetes_cluster.minimal_cluster.ready
    region            = var.civo_region
    node_count        = 1
    node_size         = "g4s.kube.small"
  }
}

output "cluster_id" {
  description = "Cluster ID"
  value       = civo_kubernetes_cluster.minimal_cluster.id
}

output "cluster_name" {
  description = "Cluster name"
  value       = civo_kubernetes_cluster.minimal_cluster.name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint"
  value       = civo_kubernetes_cluster.minimal_cluster.api_endpoint
}

output "master_ip" {
  description = "Master node IP address"
  value       = civo_kubernetes_cluster.minimal_cluster.master_ip
}

output "kubeconfig" {
  description = "Kubeconfig content"
  value       = civo_kubernetes_cluster.minimal_cluster.kubeconfig
  sensitive   = true
}

output "object_store_details" {
  description = "Object store configuration"
  value = {
    id         = civo_object_store.minimal_storage.id
    name       = civo_object_store.minimal_storage.name
    bucket_url = civo_object_store.minimal_storage.bucket_url
    size_gb    = 50
    region     = var.civo_region
  }
}

output "object_store_credentials" {
  description = "Object store credentials"
  value = {
    access_key_id     = civo_object_store_credential.minimal_credentials.access_key_id
    secret_access_key = civo_object_store_credential.minimal_credentials.secret_access_key
  }
  sensitive = true
}

output "estimated_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    cluster_node     = "$10.37"  # 1 small node
    object_store     = "$1.00"   # 50GB
    total_monthly    = "$11.37"
    note            = "Very cost-effective for development and testing!"
  }
}

output "access_info" {
  description = "How to access your deployment"
  value = {
    kubectl_config = "echo '${base64decode(civo_kubernetes_cluster.minimal_cluster.kubeconfig)}' > kubeconfig-minimal.yaml && export KUBECONFIG=$PWD/kubeconfig-minimal.yaml"
    master_ip      = civo_kubernetes_cluster.minimal_cluster.master_ip
    note          = "Services will use NodePort - check with 'kubectl get svc -n word-filter-app' for port numbers"
  }
}

output "quick_start" {
  description = "Quick start commands"
  value = [
    "# Save and use kubeconfig",
    "echo '${base64decode(civo_kubernetes_cluster.minimal_cluster.kubeconfig)}' > kubeconfig-minimal.yaml",
    "export KUBECONFIG=$PWD/kubeconfig-minimal.yaml",
    "",
    "# Check cluster status",
    "kubectl get nodes",
    "",
    "# Deploy application", 
    "kubectl apply -f ../civo-k8s-minimal/",
    "",
    "# Check deployments",
    "kubectl get pods -n word-filter-app",
    "kubectl get services -n word-filter-app",
    "",
    "# Port forward for local access",
    "kubectl port-forward -n word-filter-app service/word-filter-backend 8001:8001 &",
    "kubectl port-forward -n word-filter-app service/word-filter-frontend 4201:80 &",
    "",
    "# Open in browser",
    "echo 'Frontend: http://localhost:4201'",
    "echo 'API: http://localhost:8001'",
    "echo 'API Docs: http://localhost:8001/docs'"
  ]
}
