variable "host_project_id" {
  description = "The host project ID for the Shared VPC"
  type        = string
}

variable "service_project_id" {
  description = "The service project ID that will use the Shared VPC"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "vpc_name" {
  description = "Name of the shared VPC"
  type        = string
  default     = "gke-shared-vpc"
}

variable "subnet_name" {
  description = "Name of the GKE subnet"
  type        = string
  default     = "gke-prod-subnet"
}

variable "subnet_cidr" {
  description = "CIDR range for the subnet"
  type        = string
  default     = "10.0.0.0/20"
}

variable "pod_cidr" {
  description = "CIDR range for GKE pods (secondary IP range)"
  type        = string
  default     = "10.1.0.0/16"
}

variable "svc_cidr" {
  description = "CIDR range for GKE services (secondary IP range)"
  type        = string
  default     = "10.2.0.0/20"
}

variable "router_name" {
  description = "Name of the Cloud Router for NAT"
  type        = string
  default     = "gke2-router"
}

variable "nat_name" {
  description = "Name of the Cloud NAT"
  type        = string
  default     = "gke-nat"
}

variable "routing_mode" {
  description = "VPC routing mode (GLOBAL or REGIONAL)"
  type        = string
  default     = "GLOBAL"
}

variable "terraform_state_bucket" {
  description = "GCS bucket name for Terraform remote state"
  type        = string
}

variable "labels" {
  description = "GCP labels to apply to all resources"
  type        = map(string)
  default = {
    managed_by = "terraform"
    repo       = "prod-gke"
  }
}
