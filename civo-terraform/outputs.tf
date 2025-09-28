# Civo Infrastructure Outputs

# Cluster Information
output "cluster_details" {
  description = "Complete cluster information"
  value = {
    id               = civo_kubernetes_cluster.word_filter_cluster.id
    name             = civo_kubernetes_cluster.word_filter_cluster.name
    api_endpoint     = civo_kubernetes_cluster.word_filter_cluster.api_endpoint
    master_ip        = civo_kubernetes_cluster.word_filter_cluster.master_ip
    kubernetes_version = civo_kubernetes_cluster.word_filter_cluster.kubernetes_version
    status          = civo_kubernetes_cluster.word_filter_cluster.status
    ready           = civo_kubernetes_cluster.word_filter_cluster.ready
    node_count      = var.node_count
    node_size       = var.node_size
    region          = var.civo_region
  }
}

output "cluster_id" {
  description = "ID of the Civo Kubernetes cluster"
  value       = civo_kubernetes_cluster.word_filter_cluster.id
}

output "cluster_name" {
  description = "Name of the Civo Kubernetes cluster"
  value       = civo_kubernetes_cluster.word_filter_cluster.name
}

output "cluster_endpoint" {
  description = "Endpoint for the Kubernetes API server"
  value       = civo_kubernetes_cluster.word_filter_cluster.api_endpoint
}

output "master_ip" {
  description = "IP address of the master node"
  value       = civo_kubernetes_cluster.word_filter_cluster.master_ip
}

output "kubeconfig" {
  description = "Kubeconfig for the cluster (base64 encoded)"
  value       = civo_kubernetes_cluster.word_filter_cluster.kubeconfig
  sensitive   = true
}

# Save kubeconfig to local file for easy access
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "echo '${base64decode(civo_kubernetes_cluster.word_filter_cluster.kubeconfig)}' > kubeconfig-civo.yaml && export KUBECONFIG=$PWD/kubeconfig-civo.yaml"
}

# Network Information
output "network_details" {
  description = "Network configuration details"
  value = {
    id     = civo_network.word_filter_network.id
    name   = civo_network.word_filter_network.label
    region = var.civo_region
  }
}

output "firewall_details" {
  description = "Firewall configuration details"
  value = {
    id    = civo_firewall.word_filter_fw.id
    name  = civo_firewall.word_filter_fw.name
  }
}

# Storage Information
output "object_store_details" {
  description = "Object store configuration details"
  value = {
    id           = civo_object_store.word_filter_storage.id
    name         = civo_object_store.word_filter_storage.name
    bucket_url   = civo_object_store.word_filter_storage.bucket_url
    max_size_gb  = var.objectstore_max_size_gb
    region       = var.civo_region
  }
}

output "object_store_endpoint" {
  description = "Civo Object Store endpoint"
  value       = civo_object_store.word_filter_storage.bucket_url
}

output "object_store_credentials" {
  description = "Object store credentials"
  value = {
    access_key_id     = civo_object_store_credential.word_filter_credentials.access_key_id
    secret_access_key = civo_object_store_credential.word_filter_credentials.secret_access_key
  }
  sensitive = true
}

output "volume_details" {
  description = "Persistent volume details"
  value = {
    id       = civo_volume.word_filter_volume.id
    name     = civo_volume.word_filter_volume.name
    size_gb  = civo_volume.word_filter_volume.size_gb
    region   = var.civo_region
  }
}

# Load Balancer Information
output "load_balancer_details" {
  description = "Load balancer configuration details"
  value = {
    hostname    = civo_loadbalancer.word_filter_lb.hostname
    public_ip   = civo_loadbalancer.word_filter_lb.public_ip
    protocol    = civo_loadbalancer.word_filter_lb.protocol
    port        = civo_loadbalancer.word_filter_lb.port
    policy      = civo_loadbalancer.word_filter_lb.policy
  }
}

output "load_balancer_ip" {
  description = "Public IP of the load balancer"
  value       = civo_loadbalancer.word_filter_lb.public_ip
}

# DNS Information (if configured)
output "dns_details" {
  description = "DNS configuration details"
  value = var.domain_name != "" ? {
    domain      = var.domain_name
    subdomain   = var.subdomain
    full_domain = "${var.subdomain}.${var.domain_name}"
    record_id   = var.domain_name != "" ? civo_dns_domain_record.word_filter_dns[0].id : null
  } : null
}

# Database Information (if enabled)
output "database_details" {
  description = "Database configuration details"
  value = var.enable_database ? {
    id       = civo_database.word_filter_db[0].id
    name     = civo_database.word_filter_db[0].name
    size     = civo_database.word_filter_db[0].size
    version  = civo_database.word_filter_db[0].version
    endpoint = civo_database.word_filter_db[0].endpoint
    port     = civo_database.word_filter_db[0].port
    username = civo_database.word_filter_db[0].username
  } : null
}

output "database_connection_string" {
  description = "Database connection string (if enabled)"
  value       = var.enable_database ? "postgresql://${civo_database.word_filter_db[0].username}:${civo_database.word_filter_db[0].password}@${civo_database.word_filter_db[0].endpoint}:${civo_database.word_filter_db[0].port}/${civo_database.word_filter_db[0].name}" : null
  sensitive   = true
}

# Application URLs
output "application_urls" {
  description = "URLs to access the application"
  value = {
    load_balancer_ip = "http://${civo_loadbalancer.word_filter_lb.public_ip}"
    custom_domain    = var.domain_name != "" ? "http://${var.subdomain}.${var.domain_name}" : null
    backend_api      = "http://${civo_loadbalancer.word_filter_lb.public_ip}/api"
    api_docs         = "http://${civo_loadbalancer.word_filter_lb.public_ip}/api/docs"
  }
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly cost in USD"
  value = {
    cluster_nodes   = var.node_count * (var.node_size == "g4s.kube.small" ? 10.37 : var.node_size == "g4s.kube.medium" ? 20.73 : var.node_size == "g4s.kube.large" ? 41.46 : 82.92)
    object_store    = var.objectstore_max_size_gb * 0.02  # $0.02 per GB/month
    load_balancer   = 10  # $10/month for load balancer
    volume          = var.volume_size_gb * 0.10  # $0.10 per GB/month
    database        = var.enable_database ? (var.database_size == "g4s.db.small" ? 15 : var.database_size == "g4s.db.medium" ? 30 : 60) : 0
    total           = var.node_count * (var.node_size == "g4s.kube.small" ? 10.37 : var.node_size == "g4s.kube.medium" ? 20.73 : var.node_size == "g4s.kube.large" ? 41.46 : 82.92) + var.objectstore_max_size_gb * 0.02 + 10 + var.volume_size_gb * 0.10 + (var.enable_database ? (var.database_size == "g4s.db.small" ? 15 : var.database_size == "g4s.db.medium" ? 30 : 60) : 0)
  }
}

# Deployment Information
output "deployment_info" {
  description = "Information needed for deployment"
  value = {
    cluster_name     = civo_kubernetes_cluster.word_filter_cluster.name
    cluster_id       = civo_kubernetes_cluster.word_filter_cluster.id
    api_endpoint     = civo_kubernetes_cluster.word_filter_cluster.api_endpoint
    region           = var.civo_region
    environment      = var.environment
    backend_image    = var.backend_image
    frontend_image   = var.frontend_image
    object_store_url = civo_object_store.word_filter_storage.bucket_url
  }
}

# Commands to run after deployment
output "next_steps" {
  description = "Commands to run after Terraform deployment"
  value = [
    "# 1. Configure kubectl:",
    "echo '${base64decode(civo_kubernetes_cluster.word_filter_cluster.kubeconfig)}' > kubeconfig-civo.yaml",
    "export KUBECONFIG=$PWD/kubeconfig-civo.yaml",
    "",
    "# 2. Verify cluster is ready:",
    "kubectl get nodes",
    "kubectl get pods --all-namespaces",
    "",
    "# 3. Deploy the application:",
    "kubectl apply -f ../civo-k8s/",
    "",
    "# 4. Check application status:",
    "kubectl get pods -n word-filter-app",
    "kubectl get services -n word-filter-app",
    "",
    "# 5. Access the application:",
    "echo 'Frontend: http://${civo_loadbalancer.word_filter_lb.public_ip}'",
    "echo 'Backend API: http://${civo_loadbalancer.word_filter_lb.public_ip}:8001'",
    "echo 'API Docs: http://${civo_loadbalancer.word_filter_lb.public_ip}:8001/docs'",
  ]
}

# Monitoring URLs (if enabled)
output "monitoring_urls" {
  description = "URLs for monitoring services (if enabled)"
  value = var.enable_monitoring ? {
    prometheus = "http://${civo_loadbalancer.word_filter_lb.public_ip}:9090"
    grafana    = "http://${civo_loadbalancer.word_filter_lb.public_ip}:3000"
    alertmanager = "http://${civo_loadbalancer.word_filter_lb.public_ip}:9093"
  } : null
}

# Security Information
output "security_info" {
  description = "Security configuration information"
  value = {
    firewall_enabled           = true
    network_policies_enabled   = var.enable_network_policies
    pod_security_enabled       = var.enable_pod_security_policies
    ssl_certificates_enabled   = contains(var.civo_applications, "cert-manager")
    backup_enabled             = var.enable_backups
    monitoring_enabled         = var.enable_monitoring
    logging_enabled            = var.enable_logging
  }
}
