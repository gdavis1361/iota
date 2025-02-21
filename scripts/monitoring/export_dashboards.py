#!/usr/bin/env python3

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests


class GrafanaExporter:
    def __init__(self, grafana_url: str, api_key: str):
        self.grafana_url = grafana_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
    def get_all_dashboards(self) -> List[Dict]:
        """Get list of all dashboards."""
        response = requests.get(
            f"{self.grafana_url}/api/search?type=dash-db",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_dashboard(self, uid: str) -> Dict:
        """Get dashboard configuration by UID."""
        response = requests.get(
            f"{self.grafana_url}/api/dashboards/uid/{uid}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def export_dashboards(self, output_dir: str, backup: bool = True) -> None:
        """Export all dashboards to JSON files."""
        os.makedirs(output_dir, exist_ok=True)
        
        if backup:
            backup_dir = os.path.join(
                output_dir,
                f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            os.makedirs(backup_dir, exist_ok=True)
        
        dashboards = self.get_all_dashboards()
        for dash in dashboards:
            try:
                dashboard = self.get_dashboard(dash['uid'])
                
                # Clean up dashboard for version control
                dashboard['dashboard'].pop('version', None)
                dashboard['dashboard'].pop('id', None)
                
                # Save current version
                filename = f"{dash['uid']}.json"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w') as f:
                    json.dump(dashboard, f, indent=2, sort_keys=True)
                    
                print(f"Exported dashboard: {dash['title']} -> {filename}")
                
                # Create backup if enabled
                if backup:
                    backup_path = os.path.join(backup_dir, filename)
                    with open(backup_path, 'w') as f:
                        json.dump(dashboard, f, indent=2, sort_keys=True)
                    
            except Exception as e:
                print(f"Error exporting dashboard {dash['uid']}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Export Grafana dashboards")
    parser.add_argument("--grafana-url", default="http://localhost:3000", help="Grafana server URL")
    parser.add_argument("--api-key", required=True, help="Grafana API key")
    parser.add_argument("--output-dir", default="monitoring/grafana/dashboards", help="Output directory")
    parser.add_argument("--backup", action="store_true", help="Create backup of current dashboards")
    
    args = parser.parse_args()
    
    try:
        exporter = GrafanaExporter(args.grafana_url, args.api_key)
        exporter.export_dashboards(args.output_dir, args.backup)
        
    except Exception as e:
        print(f"Error exporting dashboards: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
