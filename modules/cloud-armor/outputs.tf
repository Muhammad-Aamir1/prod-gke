output "id" {
  description = "The ID of the security policy"
  value       = try(google_compute_security_policy.this[0].id, null)
}

output "name" {
  description = "The name of the security policy"
  value       = try(google_compute_security_policy.this[0].name, null)
}
