variable "name" {
  description = "Name of the VPC network"
  type        = string
}

variable "routing_mode" {
  description = "VPC routing mode (GLOBAL or REGIONAL)"
  type        = string
  default     = "GLOBAL"
}
