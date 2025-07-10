"""
R&D Cost Calculation Engine
Processes uploaded financial data and calculates qualifying R&D expenditure
"""

import pandas as pd
import yaml
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime


class RDProcessor:
    """Main processor for R&D cost calculations"""
    
    def __init__(self, rules_config: Optional[Dict] = None):
        """
        Initialize the processor with R&D rules configuration
        
        Args:
            rules_config: Dictionary containing R&D calculation rules
        """
        self.rules = rules_config or self._load_default_rules()
        self.data = None
        self.processed_results = {}
        
    def _load_default_rules(self) -> Dict:
        """Load default R&D calculation rules"""
        return {
            'epw_cap_percentage': 0.65,
            'nic_uplift_rate': 0.138,
            'minimum_rd_percentage': 0.0,
            'maximum_rd_percentage': 1.0,
            'excluded_cost_keywords': [],
            'grant_adjustment': True,
            'connected_epw_rules': {
                'apply_65_percent_cap': True,
                'separate_calculation': True
            }
        }
    
    def load_data(self, file_path: str, file_type: str) -> bool:
        """
        Load financial data from uploaded file
        
        Args:
            file_path: Path to the uploaded file
            file_type: Type of file (payroll, trial_balance, timesheet)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path.endswith('.xlsx'):
                self.data = pd.read_excel(file_path)
            elif file_path.endswith('.csv'):
                self.data = pd.read_csv(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            self.file_type = file_type
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def apply_column_mapping(self, mapping_config: Dict) -> bool:
        """
        Apply column mapping configuration to the data
        
        Args:
            mapping_config: Dictionary mapping standard fields to column names
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Rename columns based on mapping
            column_mapping = {}
            for standard_field, column_name in mapping_config.items():
                if column_name in self.data.columns:
                    column_mapping[column_name] = standard_field
            
            self.data = self.data.rename(columns=column_mapping)
            return True
            
        except Exception as e:
            print(f"Error applying column mapping: {e}")
            return False
    
    def calculate_rd_costs(self, employee_overrides: Optional[Dict] = None) -> Dict:
        """
        Calculate qualifying R&D costs based on the loaded data
        
        Args:
            employee_overrides: Dictionary of employee-specific R&D percentages
            
        Returns:
            Dictionary containing calculated results
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        results = {
            'total_costs': Decimal('0'),
            'qualifying_rd_costs': Decimal('0'),
            'epw_costs': Decimal('0'),
            'staff_costs': Decimal('0'),
            'excluded_costs': Decimal('0'),
            'grant_adjustments': Decimal('0'),
            'line_items': []
        }
        
        employee_overrides = employee_overrides or {}
        
        # Process each row in the data
        for index, row in self.data.iterrows():
            line_item = self._process_line_item(row, employee_overrides)
            results['line_items'].append(line_item)
            
            # Aggregate totals
            results['total_costs'] += line_item['gross_cost']
            results['qualifying_rd_costs'] += line_item['qualifying_cost']
            
            if line_item['is_epw']:
                results['epw_costs'] += line_item['qualifying_cost']
            else:
                results['staff_costs'] += line_item['qualifying_cost']
            
            if line_item['excluded']:
                results['excluded_costs'] += line_item['gross_cost']
        
        # Apply NIC uplift to staff costs
        results['staff_costs_with_nic'] = results['staff_costs'] * (1 + Decimal(str(self.rules['nic_uplift_rate'])))
        
        # Calculate final qualifying expenditure
        results['total_qualifying_expenditure'] = results['staff_costs_with_nic'] + results['epw_costs']
        
        self.processed_results = results
        return results
    
    def _process_line_item(self, row: pd.Series, employee_overrides: Dict) -> Dict:
        """
        Process a single line item from the data
        
        Args:
            row: Pandas Series representing a row of data
            employee_overrides: Employee-specific R&D percentages
            
        Returns:
            Dictionary containing processed line item data
        """
        # Extract basic information
        employee_name = row.get('employee_name', '')
        gross_cost = Decimal(str(row.get('gross_cost', 0)))
        cost_description = row.get('description', '')
        
        # Determine if this is EPW (externally provided worker)
        is_epw = row.get('is_epw', False)
        epw_connected = row.get('epw_connected', False)
        
        # Check for exclusions
        excluded = self._should_exclude_cost(cost_description, gross_cost)
        
        # Calculate R&D percentage
        rd_percentage = self._get_rd_percentage(employee_name, employee_overrides)
        
        # Calculate qualifying cost
        qualifying_cost = Decimal('0')
        if not excluded:
            qualifying_cost = gross_cost * Decimal(str(rd_percentage))
            
            # Apply EPW cap if applicable
            if is_epw:
                epw_cap = gross_cost * Decimal(str(self.rules['epw_cap_percentage']))
                qualifying_cost = min(qualifying_cost, epw_cap)
        
        return {
            'employee_name': employee_name,
            'description': cost_description,
            'gross_cost': gross_cost,
            'rd_percentage': rd_percentage,
            'qualifying_cost': qualifying_cost,
            'is_epw': is_epw,
            'epw_connected': epw_connected,
            'excluded': excluded,
            'exclusion_reason': self._get_exclusion_reason(cost_description, gross_cost)
        }
    
    def _should_exclude_cost(self, description: str, gross_cost: Decimal) -> bool:
        """
        Determine if a cost should be excluded from R&D calculations
        
        Args:
            description: Cost description
            gross_cost: Gross cost amount
            
        Returns:
            True if cost should be excluded, False otherwise
        """
        # Check for excluded keywords
        for keyword in self.rules['excluded_cost_keywords']:
            if keyword.lower() in description.lower():
                return True
        
        # Add additional exclusion logic here
        return False
    
    def _get_exclusion_reason(self, description: str, gross_cost: Decimal) -> Optional[str]:
        """
        Get the reason for excluding a cost
        
        Args:
            description: Cost description
            gross_cost: Gross cost amount
            
        Returns:
            Exclusion reason or None if not excluded
        """
        for keyword in self.rules['excluded_cost_keywords']:
            if keyword.lower() in description.lower():
                return f"Contains excluded keyword: {keyword}"
        
        return None
    
    def _get_rd_percentage(self, employee_name: str, employee_overrides: Dict) -> float:
        """
        Get the R&D percentage for an employee
        
        Args:
            employee_name: Name of the employee
            employee_overrides: Employee-specific R&D percentages
            
        Returns:
            R&D percentage as a float between 0 and 1
        """
        if employee_name in employee_overrides:
            return employee_overrides[employee_name]
        
        # Return default R&D percentage
        return 0.8  # Default 80% R&D
    
    def generate_audit_trail(self) -> List[Dict]:
        """
        Generate audit trail showing all calculation steps
        
        Returns:
            List of audit trail entries
        """
        if not self.processed_results:
            return []
        
        audit_trail = []
        
        # Add header information
        audit_trail.append({
            'timestamp': datetime.now().isoformat(),
            'action': 'calculation_started',
            'details': f"Processing {len(self.processed_results['line_items'])} line items"
        })
        
        # Add line item details
        for item in self.processed_results['line_items']:
            audit_trail.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'line_item_processed',
                'employee': item['employee_name'],
                'gross_cost': float(item['gross_cost']),
                'qualifying_cost': float(item['qualifying_cost']),
                'rd_percentage': item['rd_percentage'],
                'excluded': item['excluded'],
                'exclusion_reason': item['exclusion_reason']
            })
        
        return audit_trail 