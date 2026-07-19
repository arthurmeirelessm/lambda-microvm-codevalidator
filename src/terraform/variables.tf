variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "code_bucket_name" {
  description = "Existing bucket that stores Lambda deployment artifacts."
  type        = string
  default     = "microvm-codevalidator-poc-275573050667"
}

variable "code_key_prefix" {
  description = "Optional S3 prefix filter for object-created notifications."
  type        = string
  default     = ""
}

variable "code_key_suffix" {
  description = "Optional S3 suffix filter for object-created notifications."
  type        = string
  default     = ".zip"
}

variable "app_lambda_name" {
  description = "Application Lambda function name."
  type        = string
  default     = "webscraping-bedrock-app"
}

variable "app_lambda_s3_key" {
  description = "Initial S3 object key used to create the application Lambda."
  type        = string
}

variable "app_lambda_s3_object_version" {
  description = "Optional initial S3 object version for the application Lambda."
  type        = string
  default     = null
}

variable "bedrock_model_id" {
  description = "Default Bedrock model ID configured in the application Lambda."
  type        = string
  default     = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "deploy_lambda_name" {
  description = "Deploy Lambda function name."
  type        = string
  default     = "webscraping-bedrock-deployer"
}
