from langfuse import Langfuse

from app.config import settings


class _NoopSpan:
    def start_observation(self, **kwargs) -> "_NoopSpan":
        return self

    def update(self, **kwargs) -> "_NoopSpan":
        return self

    def end(self, **kwargs) -> "_NoopSpan":
        return self

    def set_trace_io(self, **kwargs) -> "_NoopSpan":
        return self


class _NoopLangfuse:
    def start_observation(self, **kwargs) -> _NoopSpan:
        return _NoopSpan()

    def flush(self) -> None:
        pass


_client: Langfuse | _NoopLangfuse | None = None


def get_langfuse() -> Langfuse | _NoopLangfuse:
    global _client
    if _client is None:
        if settings.langfuse_public_key and settings.langfuse_secret_key and settings.langfuse_host:
            try:
                _client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                    debug=False,
                )
            except Exception:
                _client = _NoopLangfuse()
        else:
            _client = _NoopLangfuse()
    return _client
