output "email" {
  description = "The email of the service account"
  value       = google_service_account.this.email
}

output "member" {
  description = "The IAM member format"
  value       = "serviceAccount:${google_service_account.this.email}"
}

output "name" {
  description = "The fully qualified name of the service account"
  value       = google_service_account.this.name
}
