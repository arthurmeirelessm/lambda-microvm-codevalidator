module "app_lambda" {
  source = "./modules/app_lambda"

  function_name    = var.app_lambda_name
  code_bucket_name = var.code_bucket_name
  code_s3_key      = var.app_lambda_s3_key
  code_s3_version  = var.app_lambda_s3_object_version
  aws_region       = var.aws_region
  bedrock_model_id = var.bedrock_model_id
}

module "deploy_lambda" {
  source = "./modules/deploy_lambda"

  function_name          = var.deploy_lambda_name
  aws_region             = var.aws_region
  source_bucket_name     = var.code_bucket_name
  target_lambda_function = module.app_lambda.function_name
}

module "s3_trigger" {
  source = "./modules/s3_trigger"

  bucket_name          = var.code_bucket_name
  lambda_function_arn  = module.deploy_lambda.function_arn
  lambda_function_name = module.deploy_lambda.function_name
  filter_prefix        = var.code_key_prefix
  filter_suffix        = var.code_key_suffix
}
