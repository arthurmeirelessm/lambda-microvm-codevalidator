# Terraform Structure

Estrutura mínima em Terraform para:

- `app_lambda`: Lambda principal de web scraping + Bedrock.
- `deploy_lambda`: Lambda disparada por evento de objeto no S3 para atualizar o código da Lambda principal.
- `s3_trigger`: configuração de trigger no bucket já existente `microvm-codevalidator-poc-275573050667`.

## Fluxo

1. Um novo artefato ZIP chega no bucket de código.
2. O bucket dispara a `deploy_lambda`.
3. A `deploy_lambda` lê `bucket`, `key` e `versionId` do evento S3.
4. A `deploy_lambda` chama `UpdateFunctionCode` na Lambda principal.

## Observações

- O bucket existente não é recriado aqui. Apenas a notificação `aws_s3_bucket_notification` é gerenciada.
- Se o bucket já tiver notificações fora do Terraform, esse recurso pode sobrescrevê-las.
- A Lambda principal espera um artefato ZIP já empacotado no S3.
