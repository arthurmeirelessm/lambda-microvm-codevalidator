variable "function_name" {
  type = string
}

variable "code_bucket_name" {
  type = string
}

variable "code_s3_key" {
  type = string
}

variable "code_s3_version" {
  type    = string
  default = null
}

variable "aws_region" {
  type = string
}

variable "bedrock_model_id" {
  type = string
}
