data "google_project" "service" {
  project_id = var.service_project_id
}

output "vpc_id" {
  description = "The ID of the shared VPC"
  value       = module.vpc.id
}

output "vpc_name" {
  description = "The name of the shared VPC"
  value       = module.vpc.name
}

output "vpc_self_link" {
  description = "The self-link of the shared VPC"
  value       = module.vpc.self_link
}

output "subnet_id" {
  description = "The ID of the GKE subnet"
  value       = module.subnet.id
}

output "subnet_name" {
  description = "The name of the GKE subnet"
  value       = module.subnet.name
}

output "subnet_region" {
  description = "The region of the GKE subnet"
  value       = module.subnet.region
}

output "subnet_self_link" {
  description = "The self-link of the GKE subnet"
  value       = module.subnet.self_link
}

output "secondary_pod_range_name" {
  description = "The name of the secondary IP range for pods"
  value       = module.subnet.secondary_pod_range_name
}

output "secondary_svc_range_name" {
  description = "The name of the secondary IP range for services"
  value       = module.subnet.secondary_svc_range_name
}

output "host_project_id" {
  description = "The host project ID"
  value       = var.host_project_id
}

output "service_project_number" {
  description = "The service project number (for IAM bindings)"
  value       = data.google_project.service.number
}

output "router_name" {
  description = "The name of the Cloud Router"
  value       = module.nat.router_name
}

output "nat_name" {
  description = "The name of the Cloud NAT"
  value       = module.nat.nat_name
}

output "environment" {
  description = "The deployment environment"
  value       = var.environment
}
