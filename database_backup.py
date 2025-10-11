import os
import datetime
import csv
import json
from pathlib import Path
from nicegui import ui
from connection import connection
from database_manager import db_manager

class DatabaseBackup:
    """Database backup and restore utility"""

    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

    def get_all_tables(self):
        """Get list of all tables in the database"""
        try:
            tables = connection.get_all_tables()
            # Filter out system tables
            exclude_tables = ['sysdiagrams', 'trace_xe_action_map', 'trace_xe_event_map']
            return [table for table in tables if table not in exclude_tables]
        except Exception as e:
            ui.notify(f'Error getting tables: {str(e)}', color='red')
            return []

    def backup_table_to_csv(self, table_name, backup_path):
        """Backup a single table to CSV"""
        try:
            # Get column headers
            headers = []
            connection.contogetheaders(f"SELECT * FROM {table_name}", headers)

            # Get data
            data = []
            connection.contogetrows(f"SELECT * FROM {table_name}", data)

            # Write to CSV
            with open(backup_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                writer.writerows(data)

            return True, f"Table {table_name} backed up successfully"
        except Exception as e:
            return False, f"Error backing up {table_name}: {str(e)}"

    def backup_table_to_json(self, table_name, backup_path):
        """Backup a single table to JSON"""
        try:
            # Get column headers
            headers = []
            connection.contogetheaders(f"SELECT * FROM {table_name}", headers)

            # Get data
            data = []
            connection.contogetrows(f"SELECT * FROM {table_name}", data)

            # Convert to list of dictionaries
            json_data = []
            for row in data:
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        row_dict[header] = row[i]
                    else:
                        row_dict[header] = None
                json_data.append(row_dict)

            # Write to JSON
            with open(backup_path, 'w', encoding='utf-8') as jsonfile:
                json.dump({
                    'table_name': table_name,
                    'backup_date': datetime.datetime.now().isoformat(),
                    'columns': headers,
                    'data': json_data
                }, jsonfile, indent=2, default=str)

            return True, f"Table {table_name} backed up successfully"
        except Exception as e:
            return False, f"Error backing up {table_name}: {str(e)}"

    def create_full_backup(self, format_type='csv'):
        """Create a full database backup"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_folder = self.backup_dir / f"full_backup_{timestamp}"
            backup_folder.mkdir(exist_ok=True)

            tables = self.get_all_tables()
            success_count = 0
            error_messages = []

            for table in tables:
                if format_type == 'csv':
                    backup_path = backup_folder / f"{table}.csv"
                    success, message = self.backup_table_to_csv(table, backup_path)
                elif format_type == 'json':
                    backup_path = backup_folder / f"{table}.json"
                    success, message = self.backup_table_to_json(table, backup_path)
                else:
                    success, message = False, f"Unsupported format: {format_type}"

                if success:
                    success_count += 1
                else:
                    error_messages.append(message)

            # Create backup info file
            info_file = backup_folder / "backup_info.txt"
            with open(info_file, 'w') as f:
                f.write(f"Full Database Backup\n")
                f.write(f"Date: {datetime.datetime.now()}\n")
                f.write(f"Format: {format_type.upper()}\n")
                f.write(f"Tables: {len(tables)}\n")
                f.write(f"Successful: {success_count}\n")
                f.write(f"Failed: {len(error_messages)}\n")
                if error_messages:
                    f.write("\nErrors:\n")
                    for error in error_messages:
                        f.write(f"- {error}\n")

            if success_count == len(tables):
                ui.notify(f'Full backup completed successfully! {success_count} tables backed up.', color='green')
                return True, str(backup_folder)
            else:
                ui.notify(f'Backup completed with errors. {success_count}/{len(tables)} tables backed up.', color='orange')
                return True, str(backup_folder)

        except Exception as e:
            ui.notify(f'Error creating backup: {str(e)}', color='red')
            return False, str(e)

    def get_backup_history(self):
        """Get list of all backups"""
        try:
            backups = []
            if self.backup_dir.exists():
                for backup_folder in sorted(self.backup_dir.iterdir(), reverse=True):
                    if backup_folder.is_dir() and backup_folder.name.startswith('full_backup_'):
                        info_file = backup_folder / "backup_info.txt"
                        if info_file.exists():
                            with open(info_file, 'r') as f:
                                info = f.read()
                        else:
                            info = f"Backup folder: {backup_folder.name}"

                        backups.append({
                            'name': backup_folder.name,
                            'path': str(backup_folder),
                            'date': backup_folder.stat().st_mtime,
                            'info': info
                        })
            return backups
        except Exception as e:
            ui.notify(f'Error getting backup history: {str(e)}', color='red')
            return []

    def delete_backup(self, backup_path):
        """Delete a backup folder"""
        try:
            backup_folder = Path(backup_path)
            if backup_folder.exists() and backup_folder.is_dir():
                import shutil
                shutil.rmtree(backup_folder)
                ui.notify('Backup deleted successfully', color='green')
                return True
            else:
                ui.notify('Backup folder not found', color='red')
                return False
        except Exception as e:
            ui.notify(f'Error deleting backup: {str(e)}', color='red')
            return False

    def get_backup_size(self, backup_path):
        """Get the size of a backup folder"""
        try:
            backup_folder = Path(backup_path)
            if backup_folder.exists():
                total_size = 0
                for file_path in backup_folder.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size

                # Convert to human readable format
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if total_size < 1024.0:
                        return ".1f"
                    total_size /= 1024.0
                return ".1f"
            return "0 B"
        except Exception as e:
            return "Unknown"

# Global instance
backup_manager = DatabaseBackup()
