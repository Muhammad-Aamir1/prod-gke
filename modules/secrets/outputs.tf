output "postgres_password_secret_id" {
  description = "The ID of the postgres-password secret"
  value       = google_secret_manager_secret.postgres_password.id
}

output "postgres_user_secret_id" {
  description = "The ID of the postgres-user secret"
  value       = google_secret_manager_secret.postgres_user.id
}
