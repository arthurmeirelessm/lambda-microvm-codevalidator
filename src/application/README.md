# Lambda Web Summarizer

Aplicação AWS Lambda em Python 3.12 que recebe uma URL, valida a entrada com proteção contra SSRF, faz scraping do HTML principal e usa Amazon Bedrock para produzir um resumo estruturado.

## Estrutura

- `app/`: código da aplicação.
- `tests/`: testes unitários e integração simulada.
- `template.yaml`: template SAM para validação do runtime Lambda.
- `events/`: eventos usados no `sam local invoke`.

## Dependências

`requirements.txt` contém apenas dependências de produção necessárias para scraping:

- `requests`
- `beautifulsoup4`

`boto3` não é empacotado no artefato final porque o runtime oficial da AWS Lambda já fornece essa biblioteca. Mesmo assim, ele é instalado no ambiente de desenvolvimento para testes locais e validações dentro da MicroVM.

## Execução local rápida

Para invocar o handler com um evento salvo em `events/`:

```bash
python -m app events/success.json
```

Se nenhum arquivo for informado, o comando usa `events/success.json` por padrão.
