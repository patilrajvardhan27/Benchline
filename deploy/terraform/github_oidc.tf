# Lets GitHub Actions deploy without a stored secret: it exchanges its own
# short-lived token for an Azure token, only for runs on the main branch and tags.
resource "azuread_application" "deploy" {
  display_name = "${var.name}-github-deploy"
}

resource "azuread_service_principal" "deploy" {
  client_id = azuread_application.deploy.client_id
}

resource "azuread_application_federated_identity_credential" "main_branch" {
  application_id = azuread_application.deploy.id
  display_name   = "github-main"
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/main"
  audiences      = ["api://AzureADTokenExchange"]
}

resource "azuread_application_federated_identity_credential" "tags" {
  application_id = azuread_application.deploy.id
  display_name   = "github-tags"
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/tags/*"
  audiences      = ["api://AzureADTokenExchange"]
}

resource "azurerm_role_assignment" "deploy_acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = azuread_service_principal.deploy.object_id
}

resource "azurerm_role_assignment" "deploy_aks_user" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service Cluster User Role"
  principal_id         = azuread_service_principal.deploy.object_id
}

resource "azurerm_role_assignment" "deploy_aks_rbac" {
  scope                = azurerm_kubernetes_cluster.main.id
  role_definition_name = "Azure Kubernetes Service RBAC Writer"
  principal_id         = azuread_service_principal.deploy.object_id
}
