# Образ приложения: HTTP-API и веб-страница.
#
# Модель эмбеддингов (2.2 ГБ) в образ НЕ кладётся. Иначе он раздулся бы
# до трёх гигабайт, а при смене модели пересобирался бы целиком. Вместо
# этого она скачивается при первом запуске в том, подключённый снаружи, —
# и переживает пересборку образа.

FROM python:3.12-slim

# Не писать .pyc и не буферизовать вывод: в контейнере логи должны
# появляться сразу, иначе диагностика превращается в гадание.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Зависимости отдельным слоем: пока requirements.txt не меняется,
# пересборка кода не тянет за собой повторную установку пакетов.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY eval/ ./eval/
COPY db/ ./db/

# Приложение работает не от root — обычная предосторожность: если кто-то
# найдёт дыру в веб-слое, у него не будет прав внутри контейнера.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

# Проверка живости для docker compose: она должна отвечать даже когда
# индекс пуст, иначе контейнер будет считаться сломанным до индексации.
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)" || exit 1

CMD ["uvicorn", "ragmdn.api:app", "--host", "0.0.0.0", "--port", "8000"]
