#!/usr/bin/env python
"""
Import Claim Data Script

This script provides utilities for importing and managing claim data
for the R&D Claimer application.

Usage:
    python import_claim_data.py --help
    python import_claim_data.py --import-file /path/to/data.csv --claim-id 123
    python import_claim_data.py --export-claim 123 --format excel
"""

import argparse
import sys
import os
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rd_claimer.settings')
import django
django.setup()

from claims.models import Claim, LineItem, Employee, UploadedFile
from claims.logic.processor import RDProcessor
from claims.logic.reporter import RDReporter
from django.contrib.auth.models import User

# Very very basic outline for now

class ClaimDataImporter:
    """Handles importing and processing claim data"""
    
    def __init__(self):
        self.processor = RDProcessor()
        self.errors = []
        self.warnings = []
        
    def import_csv_file(self, file_path: str, claim_id: int, file_type: str = 'payroll') -> bool:
        """
        Import data from CSV file into a claim
        
        Args:
            file_path: Path to the CSV file
            claim_id: ID of the claim to import into
            file_type: Type of file (payroll, trial_balance, timesheet)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the claim
            claim = Claim.objects.get(id=claim_id)
            
            # Load and process the data
            if self.processor.load_data(file_path, file_type):
                print(f"Successfully loaded {file_path}")
                
                # Create uploaded file record
                uploaded_file = UploadedFile.objects.create(
                    claim=claim,
                    original_filename=os.path.basename(file_path),
                    file_type=file_type,
                    file_size=os.path.getsize(file_path),
                    uploaded_by=User.objects.first()  # Use first user for script
                )
                
                # Process the data
                results = self.processor.calculate_rd_costs()
                
                # Create line items
                for item_data in results['line_items']:
                    LineItem.objects.create(
                        claim=claim,
                        uploaded_file=uploaded_file,
                        employee_name=item_data['employee_name'],
                        description=item_data['description'],
                        gross_cost=item_data['gross_cost'],
                        rd_percentage=item_data['rd_percentage'],
                        qualifying_cost=item_data['qualifying_cost'],
                        is_epw=item_data['is_epw'],
                        epw_connected=item_data['epw_connected'],
                        excluded=item_data['excluded'],
                        exclusion_reason=item_data['exclusion_reason']
                    )
                
                print(f"Imported {len(results['line_items'])} line items")
                print(f"Total qualifying expenditure: £{results['total_qualifying_expenditure']}")
                
                return True
                
            else:
                print(f"Failed to load {file_path}")
                return False
                
        except Exception as e:
            print(f"Error importing file: {e}")
            return False
    
    def export_claim_data(self, claim_id: int, format: str = 'excel', output_path: str = None) -> bool:
        """
        Export claim data to various formats
        
        Args:
            claim_id: ID of the claim to export
            format: Export format (excel, csv, json)
            output_path: Path to save the exported file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            claim = Claim.objects.get(id=claim_id)
            line_items = LineItem.objects.filter(claim=claim)
            
            if not line_items.exists():
                print(f"No data found for claim {claim_id}")
                return False
            
            # Prepare data for export
            export_data = []
            for item in line_items:
                export_data.append({
                    'employee_name': item.employee_name,
                    'description': item.description,
                    'gross_cost': float(item.gross_cost),
                    'rd_percentage': float(item.rd_percentage),
                    'qualifying_cost': float(item.qualifying_cost),
                    'is_epw': item.is_epw,
                    'epw_connected': item.epw_connected,
                    'excluded': item.excluded,
                    'exclusion_reason': item.exclusion_reason or '',
                    'created_at': item.created_at.isoformat()
                })
            
            # Generate output filename if not provided
            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"claim_{claim_id}_export_{timestamp}.{format}"
            
            # Export based on format
            if format == 'csv':
                return self._export_csv(export_data, output_path)
            elif format == 'json':
                return self._export_json(export_data, output_path)
            elif format == 'excel':
                return self._export_excel(export_data, output_path, claim)
            else:
                print(f"Unsupported format: {format}")
                return False
                
        except Exception as e:
            print(f"Error exporting claim data: {e}")
            return False
    
    def _export_csv(self, data: List[Dict], output_path: str) -> bool:
        """Export data to CSV format"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                if data:
                    writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            print(f"Exported to CSV: {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
    
    def _export_json(self, data: List[Dict], output_path: str) -> bool:
        """Export data to JSON format"""
        try:
            with open(output_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            print(f"Exported to JSON: {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
    
    def _export_excel(self, data: List[Dict], output_path: str, claim) -> bool:
        """Export data to Excel format using RDReporter"""
        try:
            # Convert data to the format expected by RDReporter
            results = {
                'line_items': data,
                'total_qualifying_expenditure': sum(item['qualifying_cost'] for item in data),
                'staff_costs_with_nic': sum(item['qualifying_cost'] for item in data if not item['is_epw']),
                'epw_costs': sum(item['qualifying_cost'] for item in data if item['is_epw']),
                'excluded_costs': sum(item['gross_cost'] for item in data if item['excluded'])
            }
            
            claim_info = {
                'company_name': claim.company_name,
                'period_start': claim.period_start,
                'period_end': claim.period_end,
                'name': claim.name
            }
            
            reporter = RDReporter(results, claim_info)
            excel_data = reporter.export_to_excel()
            
            with open(output_path, 'wb') as f:
                f.write(excel_data.read())
            
            print(f"Exported to Excel: {output_path}")
            return True
        except Exception as e:
            print(f"Error exporting Excel: {e}")
            return False
    
    def list_claims(self) -> None:
        """List all claims in the system"""
        claims = Claim.objects.all().order_by('-created_at')
        
        if not claims.exists():
            print("No claims found in the system.")
            return
        
        print(f"{'ID':<5} {'Name':<30} {'Period':<20} {'Created':<15} {'Items':<8}")
        print("-" * 85)
        
        for claim in claims:
            item_count = LineItem.objects.filter(claim=claim).count()
            period = f"{claim.period_start} to {claim.period_end}"
            created = claim.created_at.strftime('%Y-%m-%d')
            
            print(f"{claim.id:<5} {claim.name[:29]:<30} {period:<20} {created:<15} {item_count:<8}")
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that a file can be processed"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
        
        if not file_path.lower().endswith(('.csv', '.xlsx', '.xls')):
            print(f"Unsupported file type: {file_path}")
            return False
        
        try:
            # Try to load with processor
            processor = RDProcessor()
            if processor.load_data(file_path, 'payroll'):
                print(f"File validation successful: {file_path}")
                return True
            else:
                print(f"File validation failed: {file_path}")
                return False
        except Exception as e:
            print(f"File validation error: {e}")
            return False


def main():
    """Main script function"""
    parser = argparse.ArgumentParser(description='Import and manage claim data')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import data from file')
    import_parser.add_argument('--file', required=True, help='Path to the file to import')
    import_parser.add_argument('--claim-id', type=int, required=True, help='ID of the claim to import into')
    import_parser.add_argument('--type', choices=['payroll', 'trial_balance', 'timesheet'], 
                              default='payroll', help='Type of file to import')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export claim data')
    export_parser.add_argument('--claim-id', type=int, required=True, help='ID of the claim to export')
    export_parser.add_argument('--format', choices=['excel', 'csv', 'json'], 
                              default='excel', help='Export format')
    export_parser.add_argument('--output', help='Output file path')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all claims')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a file')
    validate_parser.add_argument('--file', required=True, help='Path to the file to validate')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    importer = ClaimDataImporter()
    
    if args.command == 'import':
        if importer.validate_file(args.file):
            success = importer.import_csv_file(args.file, args.claim_id, args.type)
            sys.exit(0 if success else 1)
        else:
            sys.exit(1)
    
    elif args.command == 'export':
        success = importer.export_claim_data(args.claim_id, args.format, args.output)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        importer.list_claims()
    
    elif args.command == 'validate':
        success = importer.validate_file(args.file)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main() 