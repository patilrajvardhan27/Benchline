variable "subscription_id" {
  description = "Azure subscription to deploy into."
  type        = string
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "name" {
  description = "Short lowercase name used as a prefix for resources."
  type        = string
  default     = "benchline"
}

variable "node_vm_size" {
  description = "Check the Azure pricing calculator before changing. Nodes are the main cost."
  type        = string
  default     = "Standard_B2ms"
}

variable "node_count" {
  type    = number
  default = 2
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy through OIDC."
  type        = string
}

variable "postgres_password" {
  description = "Stored in Key Vault. Pass it with TF_VAR_postgres_password, never in a file."
  type        = string
  sensitive   = true
}
