variable "router_name" {
  description = "Name of the Cloud Router"
  type        = string
}

variable "nat_name" {
  description = "Name of the Cloud NAT"
  type        = string
}

variable "region" {
  description = "GCP region for the router and NAT"
  type        = string
}

variable "network_id" {
  description = "The ID of the VPC network"
  type        = string
}
