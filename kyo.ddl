# データ仕様(UIの考慮対象外)
## ユーザーテーブル
CREATE TABLE kyo.users (
  id bigint NOT NULL PRIMARY KEY,
  uid uuid NOT NULL UNIQUE,
  oauth_provider varchar(32) ,
  oauth_subject varchar(128) ,
  name varchar(64),
  purpose smallint NOT NULL,
  created_user varchar(32),
  created_at timestamptz,
  updated_user varchar(32),
  updated_at timestamptz,
  UNIQUE (oauth_provider, oauth_subject)
);
CREATE INDEX idx_users ON kyo.users (oauth_provider,oauth_subject, uid, purpose);

## 日々の記録テーブル(過去全て)
CREATE TABLE kyo.daily_helth (
  uid uuid NOT NULL,
  record_at date NOT NULL,
  meal text,
  kcal integer,
  carbo double precision,
  lipid double precision,
  protein double precision,
  sleep_hours double precision,
  water_ml integer,
  exercise text,
  stress integer,
  mood text,
  created_user varchar(32),
  created_at timestamptz,
  updated_user varchar(32),
  updated_at timestamptz,
  PRIMARY KEY (uid, record_at)
);

## rag元データテーブル(生テキスト)
CREATE TABLE kyo.daily_rag_sources (
  id bigserial PRIMARY KEY,
  uid uuid NOT NULL,
  category_id int NOT NULL,
  record_at date NOT NULL,
  rag_text text NOT NULL,
  created_user varchar(32),
  created_at timestamptz,
  updated_user varchar(32),
  updated_at timestamptz,
  UNIQUE (uid, category_id, record_at)
);

## ragチャンクテーブル(ベクトル検索対象)
CREATE TABLE kyo.daily_rags (
  id bigserial PRIMARY KEY,
  source_id bigint NOT NULL, -- kyo.daily_rag_sources(id) 
  chunk_index int NOT NULL,
  chunk_text text NOT NULL,
  model text NOT NULL,
  rag_embedding_1536 vector(1536),
  rag_embedding_3072 vector(3072),
  created_user varchar(32),
  created_at timestamptz,
  updated_user varchar(32),
  updated_at timestamptz,
  UNIQUE (source_id, chunk_index)
);

CREATE INDEX idx_daily_rags_source ON kyo.daily_rags (source_id, chunk_index);

## categoryテーブル
CREATE TABLE kyo.category_master (
  category_id int NOT NULL PRIMARY KEY,
  name varchar(64),
  created_user varchar(32),
  created_at timestamptz,
  updated_user varchar(32),
  updated_at timestamptz
);

## 利用目的テーブル
  create table kyo.purpose_master(
    id smallint NOT NULL PRIMARY KEY,
    name varchar(64),
    created_user varchar(32),
    created_at timestamptz,
    updated_user varchar(32),
    updated_at timestamptz
  );
