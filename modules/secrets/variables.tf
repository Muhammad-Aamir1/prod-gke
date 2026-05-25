variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "postgres_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "admin"
}

variable "password_length" {
  description = "Length of the auto-generated password"
  type        = number
  default     = 24
}

variable "labels" {
  description = "GCP labels for secret resources"
  type        = map(string)
  default     = {}
}

variable "secrets_accessor_member" {
  description = "IAM member to grant secret access to (e.g. serviceAccount:xxx@..."
  type        = string
}
