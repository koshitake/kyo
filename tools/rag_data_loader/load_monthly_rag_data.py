import argparse
import calendar
import hashlib
import json
import os
import random
import time
from datetime import date
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


CATEGORY_STRESS = 1
CATEGORY_MEAL = 2
CATEGORY_EXERCISE = 3
CATEGORY_GENERAL = 4

DAILY_RAG_BASE_DATA = "[日付:%s] [category: %s] [uid: %s]"
DAILY_STRESS_RAG = "[睡眠時間: %sh] [ストレスレベル: %s/最大:5] [今日の気分: %s] [運動内容: %s]"
DAILY_MEAL_RAG = "[食事内容:%s] [水分量: %sml]"
DAILY_EXERCISE_RAG = "[睡眠時間: %sh] [水分量: %sml] [運動内容: %s]"
DAILY_GENERAL_RAG = "[食事内容:%s] [睡眠時間: %sh] [水分量: %sml] [ストレスレベル: %s/最大:5] [今日の気分: %s] [運動内容: %s]"


def load_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("DATABASE_URL が見つかりません。.env を確認してください。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="1月・2月分の健康/RAGデータを投入します。")
    parser.add_argument("--uid", help="投入対象の uid(UUID)。指定しない場合は oauth で検索します。")
    parser.add_argument("--oauth-provider", default="google", help="ユーザー検索用 oauth_provider")
    parser.add_argument("--oauth-subject", default="1", help="ユーザー検索用 oauth_subject")
    parser.add_argument("--config", default="tools/rag_data_loader/data/health_seed_config.json", help="投入設定JSON")
    return parser


def resolve_uid(cursor, uid: str | None, oauth_provider: str, oauth_subject: str, default_uid: str | None = None) -> str:
    if uid:
        return uid
    if default_uid:
        return default_uid

    cursor.execute(
        """
        SELECT uid
        FROM kyo.users
        WHERE oauth_provider = %s
          AND oauth_subject = %s
        """,
        (oauth_provider, oauth_subject),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("対象ユーザーが見つかりません。--uid か oauth 条件を確認してください。")
    return str(row[0])


def normalize_meal_format(meal: str) -> str:
    return (
        meal.replace(" 昼:", "/昼:")
        .replace(" 夜:", "/夜:")
        .replace(" 間食:", "/間食:")
    )


def generate_health_record(target_date: date, config: dict) -> dict:
    seed = int(hashlib.sha256(target_date.isoformat().encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    is_weekend = target_date.weekday() >= 5

    if is_weekend:
        meal = rng.choice(config["weekend_meals"])
        water_ml = rng.randint(1400, 1900)
        sleep_hours = round(rng.uniform(6.0, 8.5), 1)
        stress = rng.randint(1, 3)
    else:
        meal = rng.choice(config["weekday_meals"])
        water_ml = rng.randint(1700, 2400)
        sleep_hours = round(rng.uniform(5.5, 7.5), 1)
        stress = rng.randint(2, 4)

    kcal = rng.randint(1650, 2350)
    carbo = round(rng.uniform(190, 320), 1)
    lipid = round(rng.uniform(40, 85), 1)
    protein = round(rng.uniform(55, 120), 1)
    exercise = rng.choice(config["exercise_options"])
    mood = rng.choice(config["mood_options"])

    meal = normalize_meal_format(meal)

    return {
        "record_at": target_date,
        "meal": meal,
        "kcal": kcal,
        "carbo": carbo,
        "lipid": lipid,
        "protein": protein,
        "sleep_hours": sleep_hours,
        "water_ml": water_ml,
        "exercise": exercise,
        "stress": stress,
        "mood": mood,
    }


def generate_month_records(config: dict) -> list[dict]:
    records = []
    skip_dates = set(config.get("skip_dates", []))
    for ym in config["months"]:
        year, month = ym.split("-")
        year = int(year)
        month = int(month)
        _, last_day = calendar.monthrange(year, month)
        for day in range(1, last_day + 1):
            target_date = date(year, month, day)
            if target_date.isoformat() in skip_dates:
                continue
            records.append(generate_health_record(target_date, config))
    return records


def create_rag_text(category_name: str, uid: str, health: dict) -> str:
    base_data = DAILY_RAG_BASE_DATA % (health["record_at"], category_name, uid)
    if category_name == "stress":
        body = DAILY_STRESS_RAG % (health["sleep_hours"], health["stress"], health["mood"], health["exercise"])
    elif category_name == "meals":
        body = DAILY_MEAL_RAG % (health["meal"], health["water_ml"])
    elif category_name == "exercise":
        body = DAILY_EXERCISE_RAG % (health["sleep_hours"], health["water_ml"], health["exercise"])
    else:
        body = DAILY_GENERAL_RAG % (
            health["meal"],
            health["sleep_hours"],
            health["water_ml"],
            health["stress"],
            health["mood"],
            health["exercise"],
        )
    return f"{category_name}:{base_data}\n{body}"


def make_fake_embedding_1536(text: str) -> str:
    # OpenAI埋め込みの代わりに、同じテキストなら同じ値になる疑似ベクトルを作る
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    values = [f"{rng.uniform(-1.0, 1.0):.6f}" for _ in range(1536)]
    return "[" + ",".join(values) + "]"


def upsert_daily_health(cursor, uid: str, record: dict, created_user: str):
    cursor.execute(
        """
        INSERT INTO kyo.daily_helth
          (uid, record_at, meal, kcal, carbo, lipid, protein, sleep_hours, water_ml, exercise, stress, mood,
           created_user, created_at, updated_user, updated_at)
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, NOW())
        ON CONFLICT (uid, record_at)
        DO UPDATE SET
          meal = EXCLUDED.meal,
          kcal = EXCLUDED.kcal,
          carbo = EXCLUDED.carbo,
          lipid = EXCLUDED.lipid,
          protein = EXCLUDED.protein,
          sleep_hours = EXCLUDED.sleep_hours,
          water_ml = EXCLUDED.water_ml,
          exercise = EXCLUDED.exercise,
          stress = EXCLUDED.stress,
          mood = EXCLUDED.mood,
          updated_user = EXCLUDED.updated_user,
          updated_at = NOW()
        """,
        (
            uid,
            record["record_at"],
            record["meal"],
            record["kcal"],
            record["carbo"],
            record["lipid"],
            record["protein"],
            record["sleep_hours"],
            record["water_ml"],
            record["exercise"],
            record["stress"],
            record["mood"],
            created_user,
            created_user,
        ),
    )


def upsert_rag_source(cursor, uid: str, category_id: int, record_at: date, rag_text: str, created_user: str) -> int:
    cursor.execute(
        """
        INSERT INTO kyo.daily_rag_sources
          (uid, category_id, record_at, rag_text, created_user, created_at, updated_user, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, NOW())
        ON CONFLICT (uid, category_id, record_at)
        DO UPDATE SET
          rag_text = EXCLUDED.rag_text,
          updated_user = EXCLUDED.updated_user,
          updated_at = NOW()
        RETURNING id
        """,
        (uid, category_id, record_at, rag_text, created_user, created_user),
    )
    return cursor.fetchone()[0]


def upsert_rag_chunk(cursor, source_id: int, rag_text: str, created_user: str):
    cursor.execute("DELETE FROM kyo.daily_rags WHERE source_id = %s", (source_id,))
    vector = make_fake_embedding_1536(rag_text)
    rows = [(source_id, 0, rag_text, "seed-fake-embedding-1536", vector, None, created_user, created_user)]
    execute_values(
        cursor,
        """
        INSERT INTO kyo.daily_rags
          (source_id, chunk_index, chunk_text, model,
           rag_embedding_1536, rag_embedding_3072,
           created_user, created_at, updated_user, updated_at)
        VALUES %s
        """,
        rows,
        template="(%s,%s,%s,%s,%s::vector,%s,%s,NOW(),%s,NOW())",
    )


def main():
    start_time = time.time()
    args = build_parser().parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    created_user = config.get("created_user", "seed_tool")
    default_uid = config.get("default_uid")

    database_url = load_database_url()
    records = generate_month_records(config)

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cursor:
            uid = resolve_uid(cursor, args.uid, args.oauth_provider, args.oauth_subject, default_uid)
            print(f"target uid: {uid}")
            print(f"target months: {', '.join(config.get('months', []))}")
            print(f"skip dates: {config.get('skip_dates', [])}")
            print(f"total days to process: {len(records)}")

            inserted_health_count = 0
            inserted_rag_source_count = 0
            inserted_rag_chunk_count = 0

            total_days = len(records)
            for i, record in enumerate(records, start=1):
                print(f"[{i}/{total_days}] processing {record['record_at']} ...", flush=True)
                upsert_daily_health(cursor, uid, record, created_user)
                inserted_health_count += 1

                categories = [
                    ("stress", CATEGORY_STRESS),
                    ("meals", CATEGORY_MEAL),
                    ("exercise", CATEGORY_EXERCISE),
                    ("general", CATEGORY_GENERAL),
                ]
                for category_name, category_id in categories:
                    print(f"  - category: {category_name}", flush=True)
                    rag_text = create_rag_text(category_name, uid, record)
                    source_id = upsert_rag_source(
                        cursor,
                        uid=uid,
                        category_id=category_id,
                        record_at=record["record_at"],
                        rag_text=rag_text,
                        created_user=created_user,
                    )
                    inserted_rag_source_count += 1
                    upsert_rag_chunk(cursor, source_id, rag_text, created_user)
                    inserted_rag_chunk_count += 1
                print(f"[{i}/{total_days}] done {record['record_at']}", flush=True)

            print("seed completed")
            print(f"daily_helth upsert: {inserted_health_count}")
            print(f"daily_rag_sources upsert: {inserted_rag_source_count}")
            print(f"daily_rags upsert: {inserted_rag_chunk_count}")
            print(f"elapsed: {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    main()
