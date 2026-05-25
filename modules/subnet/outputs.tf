output "id" {
  description = "The ID of the subnet"
  value       = google_compute_subnetwork.this.id
}

output "name" {
  description = "The name of the subnet"
  value       = google_compute_subnetwork.this.name
}

output "region" {
  description = "The region of the subnet"
  value       = google_compute_subnetwork.this.region
}

output "self_link" {
  description = "The self-link of the subnet"
  value       = google_compute_subnetwork.this.self_link
}

output "secondary_pod_range_name" {
  description = "The name of the secondary IP range for pods"
  value       = "pod-ranges"
}

output "secondary_svc_range_name" {
  description = "The name of the secondary IP range for services"
  value       = "svc-ranges"
}
