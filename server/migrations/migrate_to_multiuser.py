"""Migration script to move existing single-user data to admin user."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from ...config import get_settings
from ...logging_config import logger


def run_migration() -> bool:
    """Run the migration to multi-user support."""
    settings = get_settings()
    data_dir = Path(__file__).resolve().parent.parent / "data"
    migration_marker = data_dir / ".migration_complete"
    
    # Check if migration already completed
    if migration_marker.exists():
        logger.info("Multi-user migration already completed")
        return True
    
    try:
        logger.info("Starting multi-user migration...")
        
        # Create users directory structure
        users_dir = data_dir / "users" / "admin"
        users_dir.mkdir(parents=True, exist_ok=True)
        
        # Migrate conversation logs
        _migrate_conversation_logs(data_dir, users_dir)
        
        # Migrate execution agent logs
        _migrate_execution_agent_logs(data_dir, users_dir)
        
        # Migrate triggers database
        _migrate_triggers_database(data_dir)
        
        # Create migration marker
        migration_marker.touch()
        
        logger.info("Multi-user migration completed successfully")
        return True
        
    except Exception as exc:
        logger.error(f"Migration failed: {exc}")
        return False


def _migrate_conversation_logs(data_dir: Path, users_dir: Path) -> None:
    """Migrate conversation logs to admin user directory."""
    conversation_dir = users_dir / "conversation"
    conversation_dir.mkdir(parents=True, exist_ok=True)
    
    # Move conversation log
    old_conversation_log = data_dir / "conversation" / "poke_conversation.log"
    new_conversation_log = conversation_dir / "poke_conversation.log"
    
    if old_conversation_log.exists():
        shutil.move(str(old_conversation_log), str(new_conversation_log))
        logger.info("Migrated conversation log")
    
    # Move working memory log
    old_working_memory = data_dir / "conversation" / "poke_working_memory.log"
    new_working_memory = conversation_dir / "poke_working_memory.log"
    
    if old_working_memory.exists():
        shutil.move(str(old_working_memory), str(new_working_memory))
        logger.info("Migrated working memory log")
    
    # Clean up old conversation directory if empty
    old_conversation_dir = data_dir / "conversation"
    if old_conversation_dir.exists() and not any(old_conversation_dir.iterdir()):
        old_conversation_dir.rmdir()
        logger.info("Removed empty conversation directory")


def _migrate_execution_agent_logs(data_dir: Path, users_dir: Path) -> None:
    """Migrate execution agent logs to admin user directory."""
    execution_agents_dir = users_dir / "execution_agents"
    execution_agents_dir.mkdir(parents=True, exist_ok=True)
    
    old_execution_dir = data_dir / "execution_agents"
    if old_execution_dir.exists():
        # Move all files from old directory
        for item in old_execution_dir.iterdir():
            if item.is_file():
                shutil.move(str(item), str(execution_agents_dir / item.name))
            elif item.is_dir():
                shutil.move(str(item), str(execution_agents_dir / item.name))
        
        logger.info("Migrated execution agent logs")
        
        # Remove old directory if empty
        if not any(old_execution_dir.iterdir()):
            old_execution_dir.rmdir()
            logger.info("Removed empty execution agents directory")


def _migrate_triggers_database(data_dir: Path) -> None:
    """Migrate triggers database to include user_id column."""
    triggers_db = data_dir / "triggers.db"
    
    if not triggers_db.exists():
        logger.info("No triggers database found, skipping migration")
        return
    
    # Create backup
    backup_db = data_dir / "triggers.db.backup"
    shutil.copy2(str(triggers_db), str(backup_db))
    logger.info("Created triggers database backup")
    
    # Add user_id column to existing triggers
    with sqlite3.connect(str(triggers_db)) as conn:
        # Check if user_id column already exists
        cursor = conn.execute("PRAGMA table_info(triggers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "user_id" not in columns:
            # Add user_id column with default value 'admin'
            conn.execute("ALTER TABLE triggers ADD COLUMN user_id TEXT DEFAULT 'admin'")
            
            # Update existing records to have 'admin' as user_id
            conn.execute("UPDATE triggers SET user_id = 'admin' WHERE user_id IS NULL")
            
            # Create index for user_id
            conn.execute("CREATE INDEX IF NOT EXISTS idx_triggers_user ON triggers (user_id)")
            
            conn.commit()
            logger.info("Updated triggers database with user_id column")
        else:
            logger.info("Triggers database already has user_id column")


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)

