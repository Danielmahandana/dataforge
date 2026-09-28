import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger("dataforge.database")

def get_engine():
    db_url = settings.DATABASE_URL
    # If using sqlite, add check_same_thread=False
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
    try:
        connect_args = {}
        if "postgresql" in db_url:
            connect_args["connect_timeout"] = 2
        engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
        # Test connection
        with engine.connect() as conn:
            pass
        return engine
    except Exception as e:
        logger.warning(
            f"Failed to connect to primary database ({db_url}): {e}. "
            f"Falling back to SQLite at {settings.SQLITE_FALLBACK_URL}."
        )
        return create_engine(
            settings.SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False}
        )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import all models so Base knows about them
    import backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Lightweight safe migration for existing SQLite / Postgres tables
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        with engine.connect() as conn:
            if "datasets" in existing_tables:
                dataset_cols = {c["name"] for c in inspector.get_columns("datasets")}
                new_dataset_cols = [
                    ("intent_id", "VARCHAR(36)"),
                    ("policy_id", "VARCHAR(100)"),
                    ("version_label", "VARCHAR(50) DEFAULT 'v1.0'"),
                    ("quality_dimensions", "JSON"),
                    ("quality_gates_status", "JSON"),
                    ("curation_summary", "JSON"),
                ]
                for col_name, col_type in new_dataset_cols:
                    if col_name not in dataset_cols:
                        conn.execute(text(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "records" in existing_tables:
                record_cols = {c["name"] for c in inspector.get_columns("records")}
                new_record_cols = [
                    ("derived_data", "JSON"),
                    ("multi_confidence", "JSON"),
                    ("source_table", "VARCHAR(255)"),
                    ("source_section", "VARCHAR(255)"),
                    ("source_row", "INTEGER"),
                    ("field_authorities", "JSON"),
                    ("curation_decision", "VARCHAR(50) DEFAULT 'unprocessed'"),
                    ("curation_reason", "TEXT"),
                    ("duplicate_status", "VARCHAR(50) DEFAULT 'none'"),
                    ("duplicate_of_id", "VARCHAR(36)"),
                ]
                for col_name, col_type in new_record_cols:
                    if col_name not in record_cols:
                        conn.execute(text(f"ALTER TABLE records ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "evidence_items" in existing_tables:
                ev_cols = {c["name"] for c in inspector.get_columns("evidence_items")}
                new_ev_cols = [
                    ("observed_source_value", "TEXT"),
                    ("relationship", "VARCHAR(255)"),
                    ("interpretation", "TEXT"),
                    ("strength", "VARCHAR(50) DEFAULT 'STRONG'"),
                    ("is_inherited", "BOOLEAN DEFAULT 0"),
                    ("inherited_from", "VARCHAR(100)"),
                ]
                for col_name, col_type in new_ev_cols:
                    if col_name not in ev_cols:
                        conn.execute(text(f"ALTER TABLE evidence_items ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "curation_decisions" in existing_tables:
                dec_cols = {c["name"] for c in inspector.get_columns("curation_decisions")}
                new_dec_cols = [
                    ("why_not", "TEXT"),
                    ("decision_method", "VARCHAR(100) DEFAULT 'DETERMINISTIC_RULES'"),
                    ("explanation_contract", "JSON"),
                    ("conflict_ids", "JSON"),
                ]
                for col_name, col_type in new_dec_cols:
                    if col_name not in dec_cols:
                        conn.execute(text(f"ALTER TABLE curation_decisions ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "curation_runs" in existing_tables:
                run_cols = {c["name"] for c in inspector.get_columns("curation_runs")}
                new_run_cols = [
                    ("engine_version", "VARCHAR(50) DEFAULT '2.2.0'"),
                    ("ruleset_version", "VARCHAR(50) DEFAULT '2024.1'"),
                    ("manifest", "JSON"),
                ]
                for col_name, col_type in new_run_cols:
                    if col_name not in run_cols:
                        conn.execute(text(f"ALTER TABLE curation_runs ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "dataset_intents" in existing_tables:
                intent_cols = {c["name"] for c in inspector.get_columns("dataset_intents")}
                new_intent_cols = [
                    ("version", "VARCHAR(50) DEFAULT '1.0.0'"),
                    ("classification_system", "VARCHAR(100) DEFAULT 'OFO_2024'"),
                    ("target_entities", "JSON"),
                    ("target_relationships", "JSON"),
                    ("review_threshold", "FLOAT DEFAULT 0.70"),
                ]
                for col_name, col_type in new_intent_cols:
                    if col_name not in intent_cols:
                        conn.execute(text(f"ALTER TABLE dataset_intents ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "curation_policies" in existing_tables:
                pol_cols = {c["name"] for c in inspector.get_columns("curation_policies")}
                new_pol_cols = [
                    ("version", "VARCHAR(50) DEFAULT '1.0.0'"),
                ]
                for col_name, col_type in new_pol_cols:
                    if col_name not in pol_cols:
                        conn.execute(text(f"ALTER TABLE curation_policies ADD COLUMN {col_name} {col_type}"))
                conn.commit()

            if "source_conflicts" in existing_tables:
                conf_cols = {c["name"] for c in inspector.get_columns("source_conflicts")}
                new_conf_cols = [
                    ("claims", "JSON"),
                    ("recommended_action", "TEXT"),
                ]
                for col_name, col_type in new_conf_cols:
                    if col_name not in conf_cols:
                        conn.execute(text(f"ALTER TABLE source_conflicts ADD COLUMN {col_name} {col_type}"))
                conn.commit()
    except Exception as e:
        logger.warning(f"Lightweight schema auto-migration notice: {e}")
