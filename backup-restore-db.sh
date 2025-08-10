#!/bin/bash
# SQLite Database Backup and Restore Script
# Usage: ./backup-restore-db.sh [backup|restore|list]

set -e

COMPOSE_FILE="ec2.yaml"
CONTAINER_NAME="sql-service"
BACKUP_DIR="./db-backups"
DB_PATH="/app/data/sqlite_service.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

case "$1" in
    "backup")
        echo "🔄 Creating database backup..."
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db"
        
        # Copy database from container to local backup
        docker-compose -f "$COMPOSE_FILE" exec -T "$CONTAINER_NAME" cat "$DB_PATH" > "$BACKUP_FILE"
        
        echo "✅ Database backed up to: $BACKUP_FILE"
        echo "📊 Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
        ;;
        
    "restore")
        if [ -z "$2" ]; then
            echo "❌ Please specify backup file to restore"
            echo "Usage: $0 restore <backup_file>"
            echo "Available backups:"
            ls -la "$BACKUP_DIR"/*.db 2>/dev/null || echo "No backups found"
            exit 1
        fi
        
        BACKUP_FILE="$2"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "❌ Backup file not found: $BACKUP_FILE"
            exit 1
        fi
        
        echo "🔄 Restoring database from: $BACKUP_FILE"
        read -p "⚠️  This will overwrite current database. Continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Stop SQL service
            docker-compose -f "$COMPOSE_FILE" stop "$CONTAINER_NAME"
            
            # Restore database
            docker-compose -f "$COMPOSE_FILE" run --rm -T "$CONTAINER_NAME" sh -c "cat > $DB_PATH" < "$BACKUP_FILE"
            
            # Start SQL service
            docker-compose -f "$COMPOSE_FILE" start "$CONTAINER_NAME"
            
            echo "✅ Database restored successfully"
        else
            echo "❌ Restore cancelled"
        fi
        ;;
        
    "list")
        echo "📁 Available database backups:"
        if ls "$BACKUP_DIR"/*.db 1> /dev/null 2>&1; then
            ls -lah "$BACKUP_DIR"/*.db
        else
            echo "No backups found in $BACKUP_DIR"
        fi
        ;;
        
    "export")
        echo "🔄 Exporting database to SQL dump..."
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        EXPORT_FILE="$BACKUP_DIR/sqlite_dump_$TIMESTAMP.sql"
        
        # Export as SQL dump
        docker-compose -f "$COMPOSE_FILE" exec -T "$CONTAINER_NAME" sqlite3 "$DB_PATH" .dump > "$EXPORT_FILE"
        
        echo "✅ Database exported to: $EXPORT_FILE"
        echo "📊 Export size: $(du -h "$EXPORT_FILE" | cut -f1)"
        ;;
        
    "import")
        if [ -z "$2" ]; then
            echo "❌ Please specify SQL dump file to import"
            echo "Usage: $0 import <dump_file.sql>"
            exit 1
        fi
        
        DUMP_FILE="$2"
        if [ ! -f "$DUMP_FILE" ]; then
            echo "❌ SQL dump file not found: $DUMP_FILE"
            exit 1
        fi
        
        echo "🔄 Importing SQL dump: $DUMP_FILE"
        read -p "⚠️  This will overwrite current database. Continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Import SQL dump
            docker-compose -f "$COMPOSE_FILE" exec -T "$CONTAINER_NAME" sqlite3 "$DB_PATH" < "$DUMP_FILE"
            
            echo "✅ SQL dump imported successfully"
        else
            echo "❌ Import cancelled"
        fi
        ;;
        
    *)
        echo "🗃️  SQLite Database Backup and Restore Tool"
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  backup              Create a database backup"
        echo "  restore <file>      Restore database from backup file"
        echo "  list                List available backups"
        echo "  export              Export database as SQL dump"
        echo "  import <file>       Import SQL dump file"
        echo ""
        echo "Examples:"
        echo "  $0 backup"
        echo "  $0 restore ./db-backups/sqlite_backup_20240101_120000.db"
        echo "  $0 list"
        echo "  $0 export"
        echo "  $0 import ./db-backups/sqlite_dump_20240101_120000.sql"
        ;;
esac 