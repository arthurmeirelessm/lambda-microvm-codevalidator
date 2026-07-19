variable "bucket_name" {
  type = string
}

variable "lambda_function_arn" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "filter_prefix" {
  type    = string
  default = ""
}

variable "filter_suffix" {
  type    = string
  default = ".zip"
}
