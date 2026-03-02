resource "google_container_cluster" "primary" {
  name                     = "prod-cluster"
  location                 = "us-central1"
  
  # Reference the Shared VPC from the Host Project
  network                  = "projects/test-project2-409608/global/networks/gke-shared-vpc"
  subnetwork               = "projects/test-project2-409608/regions/us-central1/subnetworks/gke-prod-subnet"
  
  remove_default_node_pool = true
  initial_node_count       = 1
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "pod-ranges"
    services_secondary_range_name = "svc-ranges"
  }

  # Advanced Networking & Security
  datapath_provider = "ADVANCED_DATAPATH" # Dataplane V2 (eBPF)
  
  workload_identity_config {
    workload_pool = "my-gke-project-3.svc.id.goog"
  }
  
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false # Keep false so you can run kubectl from your local machine
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  # FinOps: Aggressive Autoscaling
  cluster_autoscaling {
    autoscaling_profile = "OPTIMIZE_UTILIZATION"
  }
  
  # Enable Gateway API for advanced ingress/routing
  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }
}
