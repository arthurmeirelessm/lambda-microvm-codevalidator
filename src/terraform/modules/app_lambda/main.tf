resource "aws_iam_role" "this" {
  name = "${var.function_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "bedrock_access" {
  name = "${var.function_name}-bedrock"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = aws_iam_role.this.arn
  runtime       = "python3.12"
  handler       = "app.handler.lambda_handler"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 512

  s3_bucket         = var.code_bucket_name
  s3_key            = var.code_s3_key
  s3_object_version = var.code_s3_version

  environment {
    variables = {
      BEDROCK_MODEL_ID       = var.bedrock_model_id
      HTTP_TIMEOUT_SECONDS   = "10"
      MAX_RESPONSE_BYTES     = "2000000"
      MAX_CONTENT_CHARACTERS = "50000"
      LOG_LEVEL              = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.basic_execution,
    aws_iam_role_policy.bedrock_access,
  ]
}
