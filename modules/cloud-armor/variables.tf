variable "name" {
  description = "Name of the Cloud Armor security policy"
  type        = string
}

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "description" {
  description = "Description of the security policy"
  type        = string
  default     = "Cloud Armor WAF policy"
}

variable "rules" {
  description = "List of security policy rules"
  type = list(object({
    action      = string
    priority    = number
    description = string
    match = object({
      versioned_expr = string
      config = object({
        src_ip_ranges = list(string)
      })
    })
    rate_limit_options = optional(object({
      exceed_action          = string
      enforce_on_key         = string
      threshold_count        = number
      threshold_interval_sec = number
    }))
  }))
  default = []
}
