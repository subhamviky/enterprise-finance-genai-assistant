variable "project_id" {
  type        = string
  description = "Google Cloud project id (deploy/gcp/landscape.vars)."
}

variable "region" {
  type    = string
  default = "us-central1"

  validation {
    condition     = contains(["us-west1", "us-central1", "us-east1"], var.region)
    error_message = "Always Free regions only: us-west1, us-central1, us-east1."
  }
}

variable "image" {
  type        = string
  description = "The assistant's image in the landscape's Artifact Registry, pushed by CI."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "firestore_database" {
  type    = string
  default = "(default)"
}

variable "reconciliation_api_url" {
  type    = string
  default = "https://reconciliation-service.placeholder.run.app"
}

variable "settlement_api_url" {
  type    = string
  default = "https://settlement-service.placeholder.run.app"
}

variable "o2c_api_url" {
  type    = string
  default = "https://o2c-agent-service.placeholder.run.app"
}

variable "audit_api_url" {
  type    = string
  default = "https://audit-ai-service.placeholder.run.app"
}

variable "llm_profile" {
  type        = string
  description = "E2A provider profile: simulated (no model access) or gemini_api (free tier)."
  default     = "simulated"

  validation {
    condition     = contains(["simulated", "gemini_api"], var.llm_profile)
    error_message = "Free tier only: simulated or gemini_api."
  }
}

variable "llm_model_id" {
  type    = string
  default = ""
}

variable "gemini_api_key_secret" {
  type        = string
  description = "Secret Manager secret id holding the Gemini API key (landscape/foundation creates it, without a value)."
  default     = ""
}

variable "max_instance_count" {
  type    = number
  default = 1
}

variable "invoker_members" {
  type        = list(string)
  description = "Who may call the assistant, e.g. [\"user:ana@example.com\"]. Never public."
  default     = []

  validation {
    condition     = !contains(var.invoker_members, "allUsers") && !contains(var.invoker_members, "allAuthenticatedUsers")
    error_message = "The assistant moves money after approval: it is never public."
  }
}

variable "identity_subject_roles" {
  type        = map(list(string))
  description = "What each caller may do (E2A v1.11.0): email -> roles, tenants as \"tenant:<id>\", e.g. {\"ana@example.com\" = [\"tenant:acme\", \"investigator\"], \"bo@example.com\" = [\"tenant:acme\", \"finance-approver\"]}."
  default     = {}
}
