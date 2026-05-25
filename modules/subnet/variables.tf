variable "name" {
  description = "Name of the subnet"
  type        = string
}

variable "ip_cidr_range" {
  description = "CIDR range for the subnet"
  type        = string
}

variable "region" {
  description = "GCP region for the subnet"
  type        = string
}

variable "network_id" {
  description = "The ID of the VPC network to attach the subnet to"
  type        = string
}

variable "pod_cidr" {
  description = "CIDR range for GKE pods (secondary IP range)"
  type        = string
}

variable "svc_cidr" {
  description = "CIDR range for GKE services (secondary IP range)"
  type        = string
}
