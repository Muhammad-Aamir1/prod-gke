variable "account_id" {
  description = "ID of the GCP service account"
  type        = string
}

variable "display_name" {
  description = "Display name of the service account"
  type        = string
  default     = null
}

variable "project_id" {
  description = "The project ID"
  type        = string
}

variable "ksa_namespace" {
  description = "Kubernetes namespace for the service account binding"
  type        = string
}

variable "ksa_name" {
  description = "Kubernetes service account name"
  type        = string
}
