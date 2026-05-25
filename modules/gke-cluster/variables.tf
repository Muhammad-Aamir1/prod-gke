variable "name" {
  description = "Name of the GKE cluster"
  type        = string
}

variable "location" {
  description = "GCP region or zone for the cluster"
  type        = string
}

variable "project_id" {
  description = "The project ID for the cluster"
  type        = string
}

variable "network" {
  description = "The self-link of the VPC network"
  type        = string
}

variable "subnetwork" {
  description = "The self-link of the subnet"
  type        = string
}

variable "pod_range_name" {
  description = "Name of the secondary IP range for pods"
  type        = string
  default     = "pod-ranges"
}

variable "svc_range_name" {
  description = "Name of the secondary IP range for services"
  type        = string
  default     = "svc-ranges"
}

variable "node_locations" {
  description = "List of zones for cluster nodes"
  type        = list(string)
  default     = []
}

variable "enable_private_nodes" {
  description = "Whether to use private nodes"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Whether the master endpoint is private"
  type        = bool
  default     = false
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the GKE master endpoint"
  type        = string
  default     = "172.16.0.0/28"
}

variable "release_channel" {
  description = "GKE release channel (STABLE, REGULAR, RAPID)"
  type        = string
  default     = "STABLE"
}

variable "datapath_provider" {
  description = "Datapath provider (ADVANCED_DATAPATH or LEGACY_DATAPATH)"
  type        = string
  default     = "ADVANCED_DATAPATH"
}

variable "autoscaling_profile" {
  description = "Cluster autoscaling profile"
  type        = string
  default     = "OPTIMIZE_UTILIZATION"
}

variable "gateway_api_channel" {
  description = "Gateway API channel (CHANNEL_STANDARD, CHANNEL_DISABLED, or null to skip)"
  type        = string
  default     = "CHANNEL_STANDARD"
}

variable "enable_vpa" {
  description = "Enable Vertical Pod Autoscaling"
  type        = bool
  default     = false
}

variable "maintenance_start_time" {
  description = "Start time for maintenance window"
  type        = string
  default     = null
}

variable "maintenance_end_time" {
  description = "End time for maintenance window"
  type        = string
  default     = null
}

variable "maintenance_recurrence" {
  description = "Recurrence rule for maintenance window"
  type        = string
  default     = null
}

variable "labels" {
  description = "GCP labels for the cluster"
  type        = map(string)
  default     = {}
}
