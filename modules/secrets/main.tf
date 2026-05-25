resource "random_password" "postgres_password" {
  length           = var.password_length
  special          = true
  override_special = "!#%&*()-_=+"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

resource "google_secret_manager_secret" "postgres_password" {
  secret_id = "postgres-password"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "postgres_password_version" {
  secret      = google_secret_manager_secret.postgres_password.id
  secret_data = random_password.postgres_password.result
}

resource "google_secret_manager_secret" "postgres_user" {
  secret_id = "postgres-user"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels
}

resource "google_secret_manager_secret_version" "postgres_user_version" {
  secret      = google_secret_manager_secret.postgres_user.id
  secret_data = var.postgres_user
}

resource "google_secret_manager_secret_iam_member" "postgres_password_access" {
  secret_id = google_secret_manager_secret.postgres_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = var.secrets_accessor_member
}

resource "google_secret_manager_secret_iam_member" "postgres_user_access" {
  secret_id = google_secret_manager_secret.postgres_user.id
  role      = "roles/secretmanager.secretAccessor"
  member    = var.secrets_accessor_member
}
