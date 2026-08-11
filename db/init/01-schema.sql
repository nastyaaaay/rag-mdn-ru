-- Схема базы. Выполняется автоматически при первом создании контейнера.
--
-- Размерность вектора (1024) должна совпадать с настройкой embedding_dim
-- в src/ragmdn/config.py. Это дублирование не убрать: SQL не читает
-- конфигурацию Python. Поэтому есть тест, который сверяет два значения
-- и падает, если их развели в разные стороны.

CREATE EXTENSION IF NOT EXISTS vector;

-- Документ MDN, прошедший фильтры качества.
CREATE TABLE documents (
    id             SERIAL PRIMARY KEY,
    slug           TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    source_url     TEXT NOT NULL,
    area           TEXT NOT NULL,
    cyrillic_ratio REAL,
    char_count     INTEGER,
    indexed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN documents.cyrillic_ratio IS
    'Доля кириллицы в прозе. Ниже порога документы в базу не попадают.';

-- Фрагмент документа — единица поиска.
CREATE TABLE chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal      INTEGER NOT NULL,
    heading_path TEXT NOT NULL,
    content      TEXT NOT NULL,
    char_count   INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    embedding    vector(1024),

    -- Порядковый номер фрагмента внутри документа уникален: защита
    -- от случайной двойной загрузки одного и того же документа.
    UNIQUE (document_id, ordinal)
);

COMMENT ON COLUMN chunks.heading_path IS
    'Путь заголовков, например «Array.prototype.filter() › Описание». '
    'Приписывается к тексту перед вычислением эмбеддинга, иначе фрагменты '
    'похожих страниц справочника неразличимы.';

-- Полнотекстовый поиск — для сравнения с векторным на шаге 12.
-- Вычисляемый столбец: PostgreSQL сам поддерживает его в актуальном виде.
ALTER TABLE chunks
    ADD COLUMN content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('russian', content)) STORED;

CREATE INDEX chunks_content_tsv_idx ON chunks USING GIN (content_tsv);

-- Векторный индекс. HNSW — быстрый приблизительный поиск ближайших соседей.
-- vector_cosine_ops: близость меряется косинусным расстоянием, как принято
-- для эмбеддингов E5.
--
-- Строить индекс до загрузки данных не оптимально (быстрее было бы после),
-- но на нашем объёме — 6765 фрагментов — разница незаметна, зато схема
-- получается полностью декларативной и воспроизводимой.
CREATE INDEX chunks_embedding_idx ON chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX chunks_document_id_idx ON chunks (document_id);

-- Параметры, с которыми построен индекс: модель эмбеддингов, размеры
-- фрагментов, порог фильтра. Нужны, чтобы поиск мог убедиться, что база
-- построена той же моделью, которой считается вектор запроса. Иначе
-- расхождение проявится не ошибкой, а молча испорченной выдачей.
CREATE TABLE index_meta (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
