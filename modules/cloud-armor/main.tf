# Cloud Armor WAF policy is disabled — requires Cloud Armor API quota.
#
# To enable:
#   1. Enable Cloud Armor API in your project
#   2. Uncomment the resources below
#
# resource "google_compute_security_policy" "this" {
#   name        = var.name
#   description = var.description
#   project     = var.project_id
#
#   dynamic "rule" {
#     for_each = var.rules
#     content {
#       action      = rule.value.action
#       priority    = rule.value.priority
#       description = rule.value.description
#       match {
#         versioned_expr = rule.value.match.versioned_expr
#         config {
#           src_ip_ranges = rule.value.match.config.src_ip_ranges
#         }
#       }
#       dynamic "rate_limit_options" {
#         for_each = rule.value.rate_limit_options != null ? [rule.value.rate_limit_options] : []
#         content {
#           conform_action = "allow"
#           exceed_action  = rate_limit_options.value.exceed_action
#           enforce_on_key = rate_limit_options.value.enforce_on_key
#           rate_limit_threshold {
#             count        = rate_limit_options.value.threshold_count
#             interval_sec = rate_limit_options.value.threshold_interval_sec
#           }
#         }
#       }
#     }
#   }
# }
