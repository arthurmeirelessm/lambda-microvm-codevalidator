data "archive_file" "package" {
  type        = "zip"
  output_path = "${path.module}/deploy_lambda.zip"

  source {
    content  = file("${path.module}/src/deploy_handler.py")
    filename = "deploy_handler.py"
  }
}

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

resource "aws_iam_role_policy" "deploy_permissions" {
  name = "${var.function_name}-permissions"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:aws:s3:::${var.source_bucket_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${var.source_bucket_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:UpdateFunctionCode"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:*:function:${var.target_lambda_function}"
      }
    ]
  })
}

resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.this.arn
  runtime          = "python3.12"
  handler          = "deploy_handler.lambda_handler"
  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      TARGET_LAMBDA_FUNCTION_NAME = var.target_lambda_function
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.basic_execution,
    aws_iam_role_policy.deploy_permissions,
  ]
}
