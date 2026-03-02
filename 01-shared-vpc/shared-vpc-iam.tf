# Enable Shared VPC Host
resource "google_compute_shared_vpc_host_project" "host" {
  project = "test-project2-409608"
}

# Attach Service Project to Host Project
resource "google_compute_shared_vpc_service_project" "service" {
  host_project    = google_compute_shared_vpc_host_project.host.project
  service_project = "my-gke-project-3"
}

# Grant GKE Robot Account access to the subnet
resource "google_compute_subnetwork_iam_binding" "gke_subnet_user" {
  project    = google_compute_subnetwork.gke_subnet.project
  region     = google_compute_subnetwork.gke_subnet.region
  subnetwork = google_compute_subnetwork.gke_subnet.name
  role       = "roles/compute.networkUser"
  members = [
    "serviceAccount:service-115538526928@container-engine-robot.iam.gserviceaccount.com",
    "serviceAccount:115538526928@cloudservices.gserviceaccount.com"
  ]
}

# Grant GKE Robot Account access to manage firewall rules (required for Ingress/Gateway)
resource "google_project_iam_member" "gke_security_admin" {
  project = "test-project2-409608"
  role    = "roles/compute.securityAdmin"
  member  = "serviceAccount:service-115538526928@container-engine-robot.iam.gserviceaccount.com"
}
