from app.settings import AppSettings


def test_settings_default_values(monkeypatch) -> None:
    monkeypatch.delenv('AWS_REGION', raising=False)
    monkeypatch.delenv('BEDROCK_MODEL_ID', raising=False)
    monkeypatch.delenv('ENABLE_JAVASCRIPT_FALLBACK', raising=False)
    settings = AppSettings()
    assert settings.aws_region == 'us-east-1'
    assert settings.bedrock_model_id == 'global.anthropic.claude-sonnet-4-6'
    assert settings.enable_javascript_fallback is True


def test_settings_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv('HTTP_TIMEOUT_SECONDS', '15')
    monkeypatch.setenv('APP_TEST_MODE', 'true')
    monkeypatch.setenv('ENABLE_JAVASCRIPT_FALLBACK', 'false')
    settings = AppSettings()
    assert settings.http_timeout_seconds == 15
    assert settings.test_mode is True
    assert settings.enable_javascript_fallback is False
