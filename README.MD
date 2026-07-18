# lambda-microvm-codevalidator

Este documento registra, de forma genérica, o fluxo de comandos desde:

- criação do bucket S3;
- criação da role usada no build da imagem;
- empacotamento da estrutura `Dockerfile`, `app.py` e `requirements.txt`;
- criação da imagem da MicroVM;
- execução da MicroVM com a imagem criada.

Os valores reais da PoC foram removidos de propósito. Use placeholders e
substitua pelos nomes e ARNs corretos do seu ambiente.

## Variáveis de exemplo

```bash
AWS_REGION="<aws-region>"
ACCOUNT_ID="<aws-account-id>"
ARTIFACT_BUCKET="microvm-codevalidator-poc-${ACCOUNT_ID}"
IMAGE_NAME="code-artifact"
IMAGE_VERSION="1.0"
BASE_IMAGE_ARN="arn:aws:lambda:us-east-1:aws:microvm-image:al2023-1"
BUILD_ROLE_NAME="microvm-codevalidator-poc-build-role"
BUILD_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${BUILD_ROLE_NAME}"
IMAGE_ARN="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:microvm-image:${IMAGE_NAME}"
```

## 1. Conferência inicial

```bash
aws configure get region
aws sts get-caller-identity
aws lambda-microvms list-managed-microvm-images
```

## 2. Criação do bucket S3

Para `us-east-1`:

```bash
aws s3api create-bucket \
  --bucket "${ARTIFACT_BUCKET}" \
  --region "${AWS_REGION}"
```

Para outras regiões, normalmente seria necessário incluir
`--create-bucket-configuration`.

## 3. Criação da role de build da imagem

Neste fluxo documentado, existe apenas a criação da role de build. Não
há uma etapa separada de criação de outra role neste documento.

Trust policy:

```bash
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "<aws-account-id>"
        }
      }
    }
  ]
}
EOF
```

Criação da role:

```bash
aws iam create-role \
  --role-name "${BUILD_ROLE_NAME}" \
  --assume-role-policy-document file://trust-policy.json
```

Policy mínima de exemplo para o build:

```bash
cat > build-role-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF
```

Anexando a policy inline:

```bash
aws iam put-role-policy \
  --role-name "${BUILD_ROLE_NAME}" \
  --policy-name "<build-role-policy-name>" \
  --policy-document file://build-role-policy.json
```

## 4. Estrutura do artefato da imagem

Estrutura esperada do zip:

```text
code-artifact.zip
├── Dockerfile
├── app.py

```

Exemplo de empacotamento:

```bash
zip "${IMAGE_NAME}.zip" Dockerfile app.py 
```

Upload do artefato:

```bash
aws s3 cp "${IMAGE_NAME}.zip" \
  "s3://${ARTIFACT_BUCKET}/microvm-images/${IMAGE_NAME}/code-artifact.zip"
```

## 5. Criação da imagem da MicroVM

```bash
aws lambda-microvms create-microvm-image \
  --name "${IMAGE_NAME}" \
  --base-image-arn "${BASE_IMAGE_ARN}" \
  --build-role-arn "${BUILD_ROLE_ARN}" \
  --code-artifact "{\"uri\":\"s3://${ARTIFACT_BUCKET}/microvm-images/${IMAGE_NAME}/code-artifact.zip\"}"
```

## 6. Acompanhamento da criação da imagem

Consulta da imagem:

```bash
aws lambda-microvms get-microvm-image \
  --image-identifier "${IMAGE_ARN}"
```

Consulta dos builds:

```bash
aws lambda-microvms list-microvm-image-builds \
  --image-identifier "${IMAGE_ARN}" \
  --image-version "${IMAGE_VERSION}"
```

## 7. Execução da MicroVM usando a imagem criada

```bash
aws lambda-microvms run-microvm \
  --image-identifier "${IMAGE_ARN}" \
  --image-version "${IMAGE_VERSION}" \
  --execution-role-arn "${BUILD_ROLE_ARN}" \
  --ingress-network-connectors '[
    "arn:aws:lambda:<aws-region>:aws:network-connector:aws-network-connector:HTTP_INGRESS",
    "arn:aws:lambda:<aws-region>:aws:network-connector:aws-network-connector:SHELL_INGRESS"
  ]' \
  --egress-network-connectors '[
    "arn:aws:lambda:<aws-region>:aws:network-connector:aws-network-connector:INTERNET_EGRESS"
  ]' \
  --idle-policy '{
    "maxIdleDurationSeconds": 900,
    "suspendedDurationSeconds": 7200,
    "autoResumeEnabled": true
  }' \
  --maximum-duration-in-seconds 28800
```

## 8. Conferência da MicroVM criada

```bash
aws lambda-microvms get-microvm \
  --microvm-identifier "<microvm-id>"
```

## 9. Passo seguinte comum

Se a MicroVM for criada com `SHELL_INGRESS`, o próximo passo costuma ser:

```bash
aws lambda-microvms create-microvm-shell-auth-token \
  --microvm-identifier "<microvm-id>" \
  --expiration-in-minutes 30
```

Depois disso, a conexão costuma ser feita com `websocat` usando a porta
`8022`.
