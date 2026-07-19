import json

import app.handler as handler_module
from app.bedrock_service import BedrockSummarizer
from app.scraper import WebScraper
from app.settings import AppSettings


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.status_code = 200
        self.headers = {'Content-Type': 'text/html; charset=utf-8'}
        self.url = 'https://example.com/article'
        self.encoding = 'utf-8'

    def iter_content(self, chunk_size: int = 8192):
        for index in range(0, len(self._body), chunk_size):
            yield self._body[index:index + chunk_size]

    def close(self) -> None:
        return None


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.max_redirects = 0

    def get(self, *_args, **_kwargs):
        return self.response


class FakeBody:
    def read(self) -> bytes:
        return b'{"content": [{"type": "text", "text": "Resumo integrado"}]}'


class FakeClient:
    def invoke_model(self, **_kwargs):
        return {'body': FakeBody()}


def test_simulated_end_to_end_flow(monkeypatch) -> None:
    monkeypatch.setattr(handler_module, 'validate_url', lambda url: None)
    settings = AppSettings(bedrock_model_id='test-model')
    html = b'<html><head><title>Integration</title></head><body><main><p>This simulated integration test validates the whole handler flow without external network calls.</p></main></body></html>'
    scraper = WebScraper(settings, session=FakeSession(FakeResponse(html)))
    summarizer = BedrockSummarizer(settings, client=FakeClient())

    response = handler_module.lambda_handler(
        {'url': 'https://example.com/article'},
        None,
        scraper=scraper,
        summarizer=summarizer,
        settings=settings,
    )
    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['summary'] == 'Resumo integrado'
