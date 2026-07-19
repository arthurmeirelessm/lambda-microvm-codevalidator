resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.bucket_name}"
}

resource "aws_s3_bucket_notification" "this" {
  bucket = var.bucket_name

  lambda_function {
    lambda_function_arn = var.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.filter_prefix != "" ? var.filter_prefix : null
    filter_suffix       = var.filter_suffix != "" ? var.filter_suffix : null
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
