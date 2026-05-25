output "name" {
  description = "The name of the GKE cluster"
  value       = google_container_cluster.this.name
}

output "endpoint" {
  description = "The endpoint of the GKE cluster"
  value       = google_container_cluster.this.endpoint
  sensitive   = true
}

output "ca_certificate" {
  description = "The base64-encoded CA certificate"
  value       = google_container_cluster.this.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "location" {
  description = "The location of the GKE cluster"
  value       = google_container_cluster.this.location
}

output "id" {
  description = "The fully qualified ID of the GKE cluster"
  value       = google_container_cluster.this.id
}

output "version" {
  description = "The GKE cluster version"
  value       = google_container_cluster.this.min_master_version
}

output "workload_identity_pool" {
  description = "The Workload Identity pool"
  value       = google_container_cluster.this.workload_identity_config[0].workload_pool
}
