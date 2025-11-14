# Vault Configuration for Unison Platform
# Production-ready setup with PostgreSQL backend

# UI Configuration
ui = true

# API and Cluster Configuration
api_addr = "https://vault.unisonos.org:8200"
cluster_addr = "https://vault.unisonos.org:8201"

# Storage Backend - PostgreSQL
storage "postgresql" {
  connection_url = "postgresql://unison:${env("DB_PASSWORD")}@postgres:5432/unison_identity?sslmode=disable"
  table = "vault_kv_store"
  max_open_connections = 25
  max_idle_connections = 5
}

# Listener Configuration
listener "tcp" {
  address = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_cert_file = "/vault/tls/tls.crt"
  tls_key_file = "/vault/tls/tls.key"
  tls_client_ca_file = "/vault/tls/ca.crt"
  tls_require_and_verify_client_cert = false
  tls_prefer_server_cipher_suites = true
  tls_cipher_suites = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256:TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384:TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256"
  tls_min_version = "tls12"
  tls_max_version = "tls13"
}

# Seal Configuration - AWS KMS (optional, for production)
seal "awskms" {
  region     = "us-east-1"
  kms_key_id = "${env("VAULT_KMS_KEY_ID")}"
  access_key = "${env("AWS_ACCESS_KEY_ID")}"
  secret_key = "${env("AWS_SECRET_ACCESS_KEY")}"
}

# Logging Configuration
log_level = "info"
log_format = "json"

# Audit Device Configuration
audit_device "file" {
  file_path = "/vault/logs/audit.log"
  mode = "0640"
  format = "json"
  hmac_accessor = true
}

# Cluster Configuration (for HA)
cluster {
  name = "unison-vault-cluster"
  node_id = "${env("VAULT_NODE_ID", "vault-node-1")}"
  retry_join {
    leader_api_addr = "https://vault-leader.unisonos.org:8200"
    leader_ca_cert_file = "/vault/tls/ca.crt"
    leader_client_cert_file = "/vault/tls/vault.crt"
    leader_client_key_file = "/vault/tls/vault.key"
  }
}

# Performance Configuration
disable_mlock = true  # Set to false if using HSM
disable_cache = false
cache_size = "200MiB"

# Plugin Directory
plugin_directory = "/vault/plugins"

# Rate Limiting
raw_storage_endpoint = false
disable_sealwrap = false
disable_printable_check = true

# Recovery Configuration (for production)
recovery_shares = 5
recovery_threshold = 3

# Auto-unseal configuration (optional)
# seal "transit" {
#   address = "https://vault-hsm.unisonos.org:8200"
#   token = "${env("HSM_VAULT_TOKEN")}"
#   key_name = "unison-vault-unseal-key"
# }

# Metrics Configuration
telemetry {
  prometheus_retention_time = "24h"
  disable_hostname = true
  enable_leases_metrics = true
  enable_agent_metrics = true
}

# Enterprise Features (if using Enterprise version)
# ui {
#   enabled = true
#   listen_address = "0.0.0.0:8200"
# }

# Replication Configuration (for HA)
# replication {
#   primary {
#     token_ttl = "24h"
#     token_max_ttl = "72h"
#   }
# }
