output "resource_group" { value = azurerm_resource_group.main.name }
output "acr_login_server" { value = azurerm_container_registry.main.login_server }
output "aks_name" { value = azurerm_kubernetes_cluster.main.name }
output "key_vault_name" { value = azurerm_key_vault.main.name }
output "github_deploy_client_id" { value = azuread_application.deploy.client_id }
output "tenant_id" { value = data.azurerm_client_config.current.tenant_id }
output "csi_identity_client_id" {
  value = azurerm_kubernetes_cluster.main.key_vault_secrets_provider[0].secret_identity[0].client_id
}
