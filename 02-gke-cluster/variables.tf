variable "project_id" {
  description = "The GCP project ID for the GKE cluster (service project)"
  type        = string
}

variable "host_project_id" {
  description = "The host project ID containing the shared VPC (not used directly when vpc_project_id is set)"
  type        = string
}

variable "vpc_project_id" {
  description = "The project ID where the VPC and subnet live. Defaults to project_id (single-project). Set to host_project_id for Shared VPC."
  type        = string
}

variable "region" {
  description = "GCP region for the cluster"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "prod-cluster"
}

variable "vpc_name" {
  description = "Name of the shared VPC (in the host project)"
  type        = string
  default     = "gke-shared-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet (in the host project)"
  type        = string
  default     = "gke-prod-subnet"
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
  description = "List of zones for cluster nodes (e.g. ['us-central1-f'])"
  type        = list(string)
  default     = ["us-central1-f"]
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the GKE master endpoint"
  type        = string
  default     = "172.16.0.0/28"
}

variable "enable_private_endpoint" {
  description = "Whether the master endpoint is private (no public access)"
  type        = bool
  default     = false
}

variable "release_channel" {
  description = "GKE release channel (STABLE, REGULAR, RAPID)"
  type        = string
  default     = "STABLE"
}

variable "datapath_provider" {
  description = "Datapath provider (ADVANCED_DATAPATH for Dataplane V2 / eBPF, LEGACY_DATAPATH for standard kubenet)"
  type        = string
  default     = "ADVANCED_DATAPATH"
}

variable "autoscaling_profile" {
  description = "Cluster autoscaling profile (OPTIMIZE_UTILIZATION or BALANCED)"
  type        = string
  default     = "OPTIMIZE_UTILIZATION"
}

variable "gateway_api_channel" {
  description = "Gateway API channel (CHANNEL_STANDARD, CHANNEL_DISABLED)"
  type        = string
  default     = "CHANNEL_STANDARD"
}

variable "enable_vertical_pod_autoscaling" {
  description = "Enable Vertical Pod Autoscaling on the cluster"
  type        = bool
  default     = false
}

variable "maintenance_start_time" {
  description = "Start time for maintenance window (format: 2024-01-01T02:00:00Z)"
  type        = string
  default     = "2024-01-01T02:00:00Z"
}

variable "maintenance_end_time" {
  description = "End time for maintenance window (UTC)"
  type        = string
  default     = "2024-01-01T06:00:00Z"
}

variable "maintenance_recurrence" {
  description = "Recurrence rule for maintenance window (RFC 5545 RRULE)"
  type        = string
  default     = "FREQ=WEEKLY;BYDAY=SA,SU"
}

variable "standard_pool" {
  description = "Configuration for the standard (on-demand) node pool"
  type = object({
    name           = string
    machine_type   = string
    min_node_count = number
    max_node_count = number
    labels         = map(string)
  })
  default = {
    name           = "standard-pool"
    machine_type   = "e2-standard-4"
    min_node_count = 1
    max_node_count = 5
    labels = {
      "finops.tier" = "backend"
      "env"         = "prod"
    }
  }
}

variable "spot_pool" {
  description = "Configuration for the spot (preemptible) node pool"
  type = object({
    name           = string
    machine_type   = string
    min_node_count = number
    max_node_count = number
    labels         = map(string)
  })
  default = {
    name           = "spot-frontend-pool"
    machine_type   = "e2-standard-2"
    min_node_count = 1
    max_node_count = 10
    labels = {
      "finops.tier" = "frontend"
    }
  }
}

variable "image_type" {
  description = "Node image type (COS_CONTAINERD, UBUNTU_CONTAINERD)"
  type        = string
  default     = "COS_CONTAINERD"
}

variable "node_pool_management" {
  description = "Node pool management settings"
  type = object({
    auto_upgrade = bool
    auto_repair  = bool
  })
  default = {
    auto_upgrade = true
    auto_repair  = true
  }
}

variable "backend_sa_name" {
  description = "Name of the GCP service account for the backend application"
  type        = string
  default     = "app-backend-sa"
}

variable "backend_sa_display_name" {
  description = "Display name of the backend GCP service account"
  type        = string
  default     = "App Backend Service Account"
}

variable "backend_ksa_namespace" {
  description = "Kubernetes namespace for the backend service account"
  type        = string
  default     = "prod-ns"
}

variable "backend_ksa_name" {
  description = "Name of the Kubernetes service account for the backend"
  type        = string
  default     = "backend-ksa"
}

variable "terraform_state_bucket" {
  description = "GCS bucket name for Terraform remote state"
  type        = string
}

variable "cloud_armor_policy_name" {
  description = "Name of the Cloud Armor security policy for the frontend"
  type        = string
  default     = "prod-waf-policy"
}

variable "labels" {
  description = "GCP labels to apply to all resources"
  type        = map(string)
  default = {
    managed_by = "terraform"
    repo       = "prod-gke"
  }
}
