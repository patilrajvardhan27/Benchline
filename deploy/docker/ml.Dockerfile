FROM python:3.15-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
# Same path as the runtime stage: the venv's scripts hard-code it in their first line.
WORKDIR /srv
COPY ml-service/pyproject.toml ml-service/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY ml-service/app app

FROM python:3.15-slim
# Numeric user so Kubernetes can enforce runAsNonRoot.
RUN useradd --system --create-home --uid 10001 app
WORKDIR /srv
COPY --from=build /srv/.venv .venv
COPY --from=build /srv/app app
ENV PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
