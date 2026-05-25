output "cluster_name" {
  description = "The name of the GKE cluster"
  value       = module.cluster.name
}

output "cluster_endpoint" {
  description = "The public endpoint of the GKE cluster"
  value       = module.cluster.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "The base64-encoded CA certificate for the cluster"
  value       = module.cluster.ca_certificate
  sensitive   = true
}

output "cluster_location" {
  description = "The location (region/zone) of the GKE cluster"
  value       = module.cluster.location
}

output "cluster_id" {
  description = "The fully qualified ID of the GKE cluster"
  value       = module.cluster.id
}

output "cluster_version" {
  description = "The GKE cluster version (as determined by the release channel)"
  value       = module.cluster.version
}

output "release_channel" {
  description = "The GKE release channel"
  value       = var.release_channel
}

output "standard_pool_name" {
  description = "The name of the standard node pool"
  value       = module.standard_pool.name
}

output "spot_pool_name" {
  description = "The name of the spot node pool"
  value       = module.spot_pool.name
}

output "standard_pool_machine_type" {
  description = "The machine type of the standard node pool"
  value       = var.standard_pool.machine_type
}

output "spot_pool_machine_type" {
  description = "The machine type of the spot node pool"
  value       = var.spot_pool.machine_type
}

output "backend_sa_email" {
  description = "The email of the backend GCP service account"
  value       = module.workload_identity.email
}

output "backend_sa_member" {
  description = "The IAM member format for the backend service account"
  value       = module.workload_identity.member
}

output "workload_identity_pool" {
  description = "The Workload Identity pool for the cluster"
  value       = module.cluster.workload_identity_pool
}

output "network" {
  description = "The self-link of the VPC used by the cluster"
  value       = data.google_compute_network.shared_vpc.self_link
}

output "subnetwork" {
  description = "The self-link of the subnet used by the cluster"
  value       = data.google_compute_subnetwork.gke_subnet.self_link
}

output "environment" {
  description = "The deployment environment"
  value       = var.environment
}

output "maintenance_window" {
  description = "The maintenance window schedule (recurrence rule)"
  value       = var.maintenance_recurrence
}

output "vertical_pod_autoscaling_enabled" {
  description = "Whether Vertical Pod Autoscaling is enabled"
  value       = var.enable_vertical_pod_autoscaling
}
