"""
Quick Start Guide - Auto Backup System
=======================================

Example usage of the automatic backup system
"""

# Example 1: Backup current Python file
from utils.auto_backup import backup

backup("gui/main_gui.py")
# ✓ Creates: gui/old_versions/main_gui.py.1


# Example 2: Backup all Python files in a directory
from utils.auto_backup import AutoBackup

ab = AutoBackup()
backed_up = ab.backup_directory("gui", extensions=[".py"])
print(f"Backed up {len(backed_up)} files")


# Example 3: List all backup versions
versions = ab.list_versions("gui/main_gui.py")
for v in versions:
    print(v.name)
# Output:
# main_gui.py.1
# main_gui.py.2
# main_gui.py.3


# Example 4: Restore a specific version
ab.restore_version("gui/main_gui.py", version=2)
# ✓ Restored version 2 from gui/old_versions/main_gui.py.2
# Current version backed up to: gui/old_versions/main_gui.py.4


# Example 5: Cleanup old backups (keep last 10)
ab.cleanup_old_backups("gui/main_gui.py", keep_last=10)
# ✓ Deleted old backup: main_gui.py.1
# ✓ Deleted old backup: main_gui.py.2


# Example 6: Use in code - automatic backup before saving
def save_with_backup(filepath, content):
    """Save file with automatic backup"""
    ab = AutoBackup()
    
    # Create backup of current version
    ab.backup_file(filepath)
    
    # Write new content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✓ Saved {filepath} (backup created)")


# Example 7: Git-like workflow (manual Git is still better for real version control)
"""
For proper version control, still use Git:

git add gui/main_gui.py
git commit -m "Fixed keyboard shortcuts"
git push

The backup system is for quick local versioning during development.
"""
