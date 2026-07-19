output "app_lambda_name" {
  value = module.app_lambda.function_name
}

output "deploy_lambda_name" {
  value = module.deploy_lambda.function_name
}

output "trigger_bucket_name" {
  value = var.code_bucket_name
}
