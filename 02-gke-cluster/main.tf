locals {
  environment_labels = merge(var.labels, {
    environment = var.environment
  })
}

module "cluster" {
  source = "../modules/gke-cluster"

  name       = var.cluster_name
  location   = var.region
  project_id = var.project_id
  network    = data.google_compute_network.shared_vpc.self_link
  subnetwork = data.google_compute_subnetwork.gke_subnet.self_link

  pod_range_name = var.pod_range_name
  svc_range_name = var.svc_range_name

  datapath_provider = var.datapath_provider
  release_channel   = var.release_channel
  node_locations    = var.node_locations

  enable_private_nodes    = true
  enable_private_endpoint = var.enable_private_endpoint
  master_ipv4_cidr_block  = var.master_ipv4_cidr_block

  autoscaling_profile = var.autoscaling_profile
  enable_vpa          = var.enable_vertical_pod_autoscaling
  gateway_api_channel = var.gateway_api_channel

  maintenance_start_time = var.maintenance_start_time
  maintenance_end_time   = var.maintenance_end_time
  maintenance_recurrence = var.maintenance_recurrence

  labels = local.environment_labels
}

moved {
  from = google_container_cluster.primary
  to   = module.cluster.google_container_cluster.this
}

module "standard_pool" {
  source = "../modules/node-pool"

  name           = var.standard_pool.name
  cluster_id     = module.cluster.id
  machine_type   = var.standard_pool.machine_type
  min_node_count = var.standard_pool.min_node_count
  max_node_count = var.standard_pool.max_node_count
  spot           = false
  labels         = merge(var.standard_pool.labels, local.environment_labels)
}

moved {
  from = google_container_node_pool.standard_nodes
  to   = module.standard_pool.google_container_node_pool.this
}

module "spot_pool" {
  source = "../modules/node-pool"

  name           = var.spot_pool.name
  cluster_id     = module.cluster.id
  machine_type   = var.spot_pool.machine_type
  min_node_count = var.spot_pool.min_node_count
  max_node_count = var.spot_pool.max_node_count
  spot           = true
  labels         = merge(var.spot_pool.labels, local.environment_labels)
}

moved {
  from = google_container_node_pool.spot_nodes
  to   = module.spot_pool.google_container_node_pool.this
}

module "workload_identity" {
  source = "../modules/workload-identity"

  account_id    = var.backend_sa_name
  display_name  = var.backend_sa_display_name
  project_id    = var.project_id
  ksa_namespace = var.backend_ksa_namespace
  ksa_name      = var.backend_ksa_name
}

moved {
  from = google_service_account.app_backend_sa
  to   = module.workload_identity.google_service_account.this
}

moved {
  from = google_service_account_iam_binding.workload_identity_binding
  to   = module.workload_identity.google_service_account_iam_binding.workload_identity
}

module "secrets" {
  source = "../modules/secrets"

  project_id = var.project_id
  labels = merge(var.labels, {
    app  = "postgres"
    env  = var.environment
    tier = "database"
  })
  secrets_accessor_member = "serviceAccount:${module.workload_identity.email}"
}

moved {
  from = random_password.postgres_password
  to   = module.secrets.random_password.postgres_password
}

moved {
  from = google_secret_manager_secret.postgres_password
  to   = module.secrets.google_secret_manager_secret.postgres_password
}

moved {
  from = google_secret_manager_secret_version.postgres_password_version
  to   = module.secrets.google_secret_manager_secret_version.postgres_password_version
}

moved {
  from = google_secret_manager_secret.postgres_user
  to   = module.secrets.google_secret_manager_secret.postgres_user
}

moved {
  from = google_secret_manager_secret_version.postgres_user_version
  to   = module.secrets.google_secret_manager_secret_version.postgres_user_version
}

moved {
  from = google_secret_manager_secret_iam_member.postgres_secrets_access
  to   = module.secrets.google_secret_manager_secret_iam_member.postgres_password_access
}

moved {
  from = google_secret_manager_secret_iam_member.postgres_user_secrets_access
  to   = module.secrets.google_secret_manager_secret_iam_member.postgres_user_access
}
