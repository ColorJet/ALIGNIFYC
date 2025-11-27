"""
Automatic file backup and versioning utility
Creates numbered backups (.py.1, .py.2) in old_versions folder
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


class AutoBackup:
    """Automatic file backup manager"""
    
    def __init__(self, backup_dir="old_versions"):
        self.backup_dir = backup_dir
        
    def backup_file(self, filepath):
        """Create a numbered backup of a file"""
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                return None
                
            # Create backup directory in same location as file
            backup_dir = filepath.parent / self.backup_dir
            backup_dir.mkdir(exist_ok=True)
            
            # Find next available version number
            version = 1
            while True:
                backup_name = f"{filepath.name}.{version}"
                backup_path = backup_dir / backup_name
                if not backup_path.exists():
                    break
                version += 1
            
            # Copy file with metadata
            shutil.copy2(filepath, backup_path)
            
            # Add timestamp to backup metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(backup_dir / f"{filepath.name}.log", "a") as log:
                log.write(f"Version {version}: {timestamp}\n")
            
            print(f"✓ Backup created: {backup_path.relative_to(filepath.parent.parent)}")
            return backup_path
            
        except Exception as e:
            print(f"✗ Backup failed for {filepath}: {e}")
            return None
    
    def backup_directory(self, directory, extensions=None):
        """Backup all files with specific extensions in a directory"""
        directory = Path(directory)
        extensions = extensions or [".py"]
        
        backed_up = []
        for ext in extensions:
            for filepath in directory.rglob(f"*{ext}"):
                if self.backup_dir not in str(filepath):
                    backup_path = self.backup_file(filepath)
                    if backup_path:
                        backed_up.append(backup_path)
        
        return backed_up
    
    def list_versions(self, filepath):
        """List all backup versions of a file"""
        filepath = Path(filepath)
        backup_dir = filepath.parent / self.backup_dir
        
        if not backup_dir.exists():
            return []
        
        versions = []
        for backup_file in sorted(backup_dir.glob(f"{filepath.name}.*")):
            if backup_file.suffix[1:].isdigit():
                versions.append(backup_file)
        
        return versions
    
    def restore_version(self, filepath, version):
        """Restore a specific backup version"""
        filepath = Path(filepath)
        backup_dir = filepath.parent / self.backup_dir
        backup_file = backup_dir / f"{filepath.name}.{version}"
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup version {version} not found")
        
        # Create backup of current file before restoring
        current_backup = self.backup_file(filepath)
        
        # Restore the backup
        shutil.copy2(backup_file, filepath)
        print(f"✓ Restored version {version} from {backup_file}")
        print(f"  Current version backed up to: {current_backup}")
        
        return filepath
    
    def cleanup_old_backups(self, filepath, keep_last=10):
        """Delete old backup versions, keeping only the most recent ones"""
        versions = self.list_versions(filepath)
        
        if len(versions) > keep_last:
            for old_version in versions[:-keep_last]:
                old_version.unlink()
                print(f"✓ Deleted old backup: {old_version.name}")


# Convenience function for quick backups
def backup(filepath):
    """Quick backup of a file"""
    ab = AutoBackup()
    return ab.backup_file(filepath)


if __name__ == "__main__":
    # Test the backup system
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        backup(filepath)
    else:
        # Backup all Python files in gui directory
        ab = AutoBackup()
        backed_up = ab.backup_directory("gui", extensions=[".py"])
        print(f"\n✓ Backed up {len(backed_up)} files")
