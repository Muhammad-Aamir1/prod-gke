# Shared VPC IAM bindings are only needed in multi-project setups.
# For single-project deployment, the GKE service agent has automatic access.
# 
# To enable Shared VPC (recommended for production), uncomment:
#
# data "google_project" "service" {
#   project_id = var.service_project_id
# }
#
# resource "google_compute_shared_vpc_host_project" "host" {
#   project = var.host_project_id
# }
#
# resource "google_compute_shared_vpc_service_project" "service" {
#   host_project    = google_compute_shared_vpc_host_project.host.project
#   service_project = var.service_project_id
# }
#
# resource "google_compute_subnetwork_iam_binding" "gke_subnet_user" {
#   project    = google_compute_subnetwork.gke_subnet.project
#   region     = google_compute_subnetwork.gke_subnet.region
#   subnetwork = google_compute_subnetwork.gke_subnet.name
#   role       = "roles/compute.networkUser"
#   members = [
#     "serviceAccount:service-${data.google_project.service.number}@container-engine-robot.iam.gserviceaccount.com",
#     "serviceAccount:${data.google_project.service.number}@cloudservices.gserviceaccount.com"
#   ]
# }
#
# resource "google_project_iam_member" "gke_security_admin" {
#   project = var.host_project_id
#   role    = "roles/compute.securityAdmin"
#   member  = "serviceAccount:service-${data.google_project.service.number}@container-engine-robot.iam.gserviceaccount.com"
# }
