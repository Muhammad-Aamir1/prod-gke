output "router_name" {
  description = "The name of the Cloud Router"
  value       = google_compute_router.this.name
}

output "router_region" {
  description = "The region of the Cloud Router"
  value       = google_compute_router.this.region
}

output "nat_name" {
  description = "The name of the Cloud NAT"
  value       = google_compute_router_nat.this.name
}
