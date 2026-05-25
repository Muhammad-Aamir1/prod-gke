variable "name" {
  description = "Name of the node pool"
  type        = string
}

variable "cluster_id" {
  description = "The ID of the GKE cluster"
  type        = string
}

variable "machine_type" {
  description = "Machine type for nodes"
  type        = string
}

variable "min_node_count" {
  description = "Minimum number of nodes"
  type        = number
}

variable "max_node_count" {
  description = "Maximum number of nodes"
  type        = number
}

variable "spot" {
  description = "Whether to use spot/preemptible instances"
  type        = bool
  default     = false
}

variable "image_type" {
  description = "Node image type"
  type        = string
  default     = "COS_CONTAINERD"
}

variable "disk_type" {
  description = "Disk type for nodes"
  type        = string
  default     = "pd-standard"
}

variable "disk_size_gb" {
  description = "Disk size in GB"
  type        = number
  default     = 50
}

variable "auto_upgrade" {
  description = "Enable auto-upgrade for nodes"
  type        = bool
  default     = true
}

variable "auto_repair" {
  description = "Enable auto-repair for nodes"
  type        = bool
  default     = true
}

variable "enable_secure_boot" {
  description = "Enable secure boot for shielded nodes"
  type        = bool
  default     = true
}

variable "workload_metadata_mode" {
  description = "Workload metadata mode (GKE_METADATA or GKE_METADATA_SERVER)"
  type        = string
  default     = "GKE_METADATA"
}

variable "labels" {
  description = "GCP labels for the node pool"
  type        = map(string)
  default     = {}
}
