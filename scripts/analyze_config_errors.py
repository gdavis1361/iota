#!/usr/bin/env python3
"""Analyze configuration errors from log files."""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from pathlib import Path

# ANSI color codes
COLORS = {
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'RESET': '\033[0m',
    'BOLD': '\033[1m'
}

class ConfigLogAnalyzer:
    """Analyzer for configuration logs."""
    
    def __init__(self, log_files: List[str]):
        self.log_files = log_files
        self.errors: List[Dict] = []
        self.error_counts = Counter()
        self.field_errors = Counter()
        self.file_errors: Dict[str, int] = {}
        
    def load_logs(self, days: Optional[int] = None) -> None:
        """Load and parse log entries from multiple files."""
        cutoff = None
        if days:
            # Use timezone-aware datetime for comparison
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
        for log_file in self.log_files:
            try:
                with open(log_file) as f:
                    file_errors = 0
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if entry.get("level") == "ERROR" and "CONFIG" in entry.get("category", ""):
                                if cutoff:
                                    # Parse timestamp with timezone info
                                    log_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                                    # Convert to UTC for comparison
                                    log_time = log_time.astimezone(timezone.utc)
                                    if log_time < cutoff:
                                        continue
                                
                                entry["source_file"] = log_file
                                self.errors.append(entry)
                                self.error_counts[entry["message"]] += 1
                                if "field" in entry.get("extra", {}):
                                    self.field_errors[entry["extra"]["field"]] += 1
                                file_errors += 1
                        except (json.JSONDecodeError, KeyError):
                            continue
                    self.file_errors[log_file] = file_errors
            except FileNotFoundError:
                print(f"{COLORS['RED']}Error: Could not open log file: {log_file}{COLORS['RESET']}")
    
    def print_summary(self) -> None:
        """Print error analysis summary with color."""
        print(f"\n{COLORS['BOLD']}=== Configuration Error Analysis ==={COLORS['RESET']}\n")
        
        # Print file summary
        print(f"{COLORS['CYAN']}Log Files Analyzed:{COLORS['RESET']}")
        for file, count in self.file_errors.items():
            print(f"  {Path(file).name}: {count} errors")
        
        print(f"\n{COLORS['BOLD']}Total Errors:{COLORS['RESET']} {len(self.errors)}")
        
        print(f"\n{COLORS['YELLOW']}Top Error Messages:{COLORS['RESET']}")
        for msg, count in self.error_counts.most_common(5):
            print(f"  {count:3d}: {msg}")
            
        print(f"\n{COLORS['MAGENTA']}Most Problematic Fields:{COLORS['RESET']}")
        for field, count in self.field_errors.most_common(5):
            print(f"  {count:3d}: {field}")
            
        print(f"\n{COLORS['RED']}Recent Error Examples:{COLORS['RESET']}")
        for error in self.errors[-3:]:
            print(f"\n  {COLORS['BLUE']}Time:{COLORS['RESET']} {error['timestamp']}")
            print(f"  {COLORS['BLUE']}File:{COLORS['RESET']} {Path(error['source_file']).name}")
            print(f"  {COLORS['BLUE']}Message:{COLORS['RESET']} {error['message']}")
            print(f"  {COLORS['BLUE']}Details:{COLORS['RESET']} {json.dumps(error.get('extra', {}), indent=2)}")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(f"{COLORS['RED']}Usage: analyze_config_errors.py <log_file1> [log_file2 ...] [--days=N]{COLORS['RESET']}")
        sys.exit(1)
        
    # Parse arguments
    log_files = []
    days = None
    
    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            try:
                days = int(arg.split("=")[1])
            except (IndexError, ValueError):
                print(f"{COLORS['RED']}Invalid days argument. Use --days=N where N is a number.{COLORS['RESET']}")
                sys.exit(1)
        else:
            log_files.append(arg)
    
    if not log_files:
        print(f"{COLORS['RED']}Error: No log files specified{COLORS['RESET']}")
        sys.exit(1)
    
    analyzer = ConfigLogAnalyzer(log_files)
    analyzer.load_logs(days)
    analyzer.print_summary()

if __name__ == "__main__":
    main()
