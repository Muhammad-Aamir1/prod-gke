#create the GCP Service Account for the application backend
resource "google_service_account" "app_backend_sa" {
  account_id   = "app-backend-sa"
  display_name = "App Backend Service Account"
  project      = "my-gke-project-3"
}

# Allow the Kubernetes Service Account (which we will create later in YAML) to impersonate this GCP SA
resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.app_backend_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:my-gke-project-3.svc.id.goog[prod-ns/backend-ksa]"
  ]
}
