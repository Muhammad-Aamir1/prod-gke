# Cloud Armor WAF policy is disabled — requires Cloud Armor API quota.
# 
# To enable:
#   1. Request Cloud Armor quota increase in your project
#   2. Or use `gcloud compute security-policies create` (basic tier)
#   3. Uncomment the resources below and update cloud-armor.tf
#
# resource "google_compute_security_policy" "frontend_waf" {
#   name        = var.cloud_armor_policy_name
#   description = "Cloud Armor security policy with rate limiting"
#   project     = var.project_id
# 
#   rule {
#     action   = "throttle"
#     priority = 1000
#     match {
#       versioned_expr = "SRC_IPS_V1"
#       config {
#         src_ip_ranges = ["*"]
#       }
#     }
#     rate_limit_options {
#       conform_action = "allow"
#       exceed_action  = "deny(429)"
#       enforce_on_key = "IP"
#       rate_limit_threshold {
#         count        = 100
#         interval_sec = 60
#       }
#     }
#     description = "Rate limit: 100 requests per IP per 60 seconds"
#   }
# 
#   rule {
#     action   = "allow"
#     priority = 2147483647
#     match {
#       versioned_expr = "SRC_IPS_V1"
#       config {
#         src_ip_ranges = ["*"]
#       }
#     }
#     description = "Default allow all other traffic"
#   }
# }
