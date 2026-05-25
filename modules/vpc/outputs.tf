output "id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.this.id
}

output "name" {
  description = "The name of the VPC network"
  value       = google_compute_network.this.name
}

output "self_link" {
  description = "The self-link of the VPC network"
  value       = google_compute_network.this.self_link
}
