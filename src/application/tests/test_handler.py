import json

import pytest

import app.handler as handler_module
from app.exceptions import BedrockInvocationError, InvalidUrlError, ScrapingError
from app.scraper import ScrapedPage
from app.settings import AppSettings


class FakeScraper:
    def __init__(self, page: ScrapedPage | None = None, error: Exception | None = None) -> None:
        self.page = page
        self.error = error

    def scrape(self, url: str) -> ScrapedPage:
        if self.error is not None:
            raise self.error
        assert self.page is not None
        return self.page


class FakeSummarizer:
    def __init__(self, summary: str = 'Resumo pronto', error: Exception | None = None) -> None:
        self.summary = summary
        self.error = error

    def summarize(self, source_url: str, title: str, content: str) -> str:
        if self.error is not None:
            raise self.error
        return self.summary


def test_handler_success_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    page = ScrapedPage(
        url='https://example.com/article',
        title='Title',
        content='Important content that is long enough for summarization.',
        content_length=56,
        status_code=200,
    )
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        scraper=FakeScraper(page=page),
        summarizer=FakeSummarizer('Resumo final'),
        settings=AppSettings(),
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['summary'] == 'Resumo final'


def test_handler_returns_validation_error() -> None:
    response = handler_module.lambda_handler({'body': '{invalid json}'}, None, settings=AppSettings())
    body = json.loads(response['body'])
    assert response['statusCode'] == 400
    assert body['error'] == 'INVALID_REQUEST'


def test_handler_returns_scraping_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        scraper=FakeScraper(error=ScrapingError('Não foi possível extrair o conteúdo da página.')),
        summarizer=FakeSummarizer(),
        settings=AppSettings(),
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 422
    assert body['error'] == 'SCRAPING_FAILED'


def test_handler_returns_bedrock_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    page = ScrapedPage(
        url='https://example.com/article',
        title='Title',
        content='Important content that is long enough for summarization.',
        content_length=56,
        status_code=200,
    )
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        scraper=FakeScraper(page=page),
        summarizer=FakeSummarizer(error=BedrockInvocationError('Não foi possível processar o conteúdo.')),
        settings=AppSettings(),
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 500
    assert body['error'] == 'INTERNAL_ERROR'


def test_handler_accepts_api_gateway_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    page = ScrapedPage(
        url='https://example.com/article',
        title='Title',
        content='Important content that is long enough for summarization.',
        content_length=56,
        status_code=200,
    )
    response = handler_module.lambda_handler(
        {'body': '{"url": "https://example.com/article"}'},
        None,
        scraper=FakeScraper(page=page),
        summarizer=FakeSummarizer(),
        settings=AppSettings(),
    )
    assert response['statusCode'] == 200


def test_handler_returns_json_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    page = ScrapedPage(
        url='https://example.com/article',
        title='Title',
        content='Important content that is long enough for summarization.',
        content_length=56,
        status_code=200,
    )
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        scraper=FakeScraper(page=page),
        summarizer=FakeSummarizer(),
        settings=AppSettings(),
    )
    assert response['headers']['Content-Type'] == 'application/json'


def test_handler_returns_invalid_url_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        handler_module,
        'validate_url',
        lambda url: (_ for _ in ()).throw(InvalidUrlError('A URL informada é inválida.')),
    )
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        settings=AppSettings(),
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 400
    assert body['error'] == 'INVALID_URL'


def test_handler_test_mode_uses_embedded_components(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    settings = AppSettings(
        test_mode=True,
        test_page_title='Página de teste',
        test_page_content='Conteúdo controlado para o modo de teste com texto suficiente.',
        test_summary='Resumo controlado',
    )
    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        settings=settings,
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['title'] == 'Página de teste'
    assert body['summary'] == 'Resumo controlado'


def test_builders_return_runtime_components() -> None:
    runtime_settings = AppSettings(test_mode=False)
    test_settings = AppSettings(test_mode=True)
    assert isinstance(handler_module._build_scraper(runtime_settings), handler_module.WebScraper)
    assert isinstance(
        handler_module._build_summarizer(runtime_settings),
        handler_module.BedrockSummarizer,
    )
    assert isinstance(
        handler_module._build_scraper(test_settings),
        handler_module.TestModeScraper,
    )
    assert isinstance(
        handler_module._build_summarizer(test_settings),
        handler_module.TestModeSummarizer,
    )


def test_log_error_uses_exception_logger_in_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(handler_module.logger, 'exception', lambda message: calls.append(message))
    handler_module._log_error('debug message', RuntimeError('boom'), AppSettings(log_level='DEBUG'))
    assert calls == ['debug message']


def test_run_local_reads_event_file_and_prints_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    event_path = tmp_path / 'event.json'
    event_path.write_text('{"url":"https://example.com/article"}', encoding='utf-8')

    monkeypatch.setattr(handler_module.sys, 'argv', ['handler.py', str(event_path)])
    monkeypatch.setattr(
        handler_module,
        'lambda_handler',
        lambda event, context: {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'received': event['url']}),
        },
    )

    assert handler_module._run_local() == 0
    printed = capsys.readouterr().out
    assert 'https://example.com/article' in printed
