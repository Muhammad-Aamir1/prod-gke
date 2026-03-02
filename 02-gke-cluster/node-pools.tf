#standard Pool (For Backend APIs, DBs, monitoring tools)
resource "google_container_node_pool" "standard_nodes" {
  name       = "standard-pool"
  cluster    = google_container_cluster.primary.id
  
  autoscaling {
    min_node_count = 1
    max_node_count = 5
  }

  node_config {
    machine_type = "e2-standard-4"
    shielded_instance_config {
      enable_secure_boot = true
    }
    labels = {
      "finops.tier" = "backend"
      "env"         = "prod"
    }
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# Spot Pool (For Stateless Frontend React apps)
resource "google_container_node_pool" "spot_nodes" {
  name       = "spot-frontend-pool"
  cluster    = google_container_cluster.primary.id
  
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }

  node_config {
    machine_type = "e2-standard-2"
    spot         = true
    shielded_instance_config {
      enable_secure_boot = true
    }
    labels = {
      "finops.tier" = "frontend"
    }
    taint { 
        key    = "cloud.google.com/gke-spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}
