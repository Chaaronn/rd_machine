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
            import os
            
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValueError("File is empty")
            
            # Try to read the file based on extension
            if file_path.lower().endswith('.xlsx'):
                try:
                    self.data = pd.read_excel(file_path, engine='openpyxl')
                except Exception as excel_error:
                    if "not a zip file" in str(excel_error).lower():
                        raise ValueError("File appears to be corrupted or not a valid Excel file. Please check the file format.")
                    else:
                        raise ValueError(f"Cannot read Excel file: {excel_error}")
            elif file_path.lower().endswith('.csv'):
                try:
                    self.data = pd.read_csv(file_path)
                except Exception as csv_error:
                    # Try different encodings for CSV
                    try:
                        self.data = pd.read_csv(file_path, encoding='latin-1')
                    except:
                        raise ValueError(f"Cannot read CSV file: {csv_error}")
            else:
                raise ValueError(f"Unsupported file format: {file_path}. Please use .xlsx or .csv files.")
            
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
    
    def aggregate_employee_data(self) -> pd.DataFrame:
        """
        Aggregate payroll data by employee, summing amounts and handling R&D percentages
        
        Returns:
            DataFrame with one row per employee containing aggregated data
        """
        if self.data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        # Group by employee name and aggregate
        aggregated_data = []
        
        for employee_name, group in self.data.groupby('Name'):
            # Sum financial amounts
            total_gross = group['Gross'].sum()
            total_er_ni = group['ErNI'].sum()
            total_er_pen = group['ErPen'].sum()
            total_bonus = group['Bonus'].sum() if 'Bonus' in group.columns else 0
            total_pilon = group['PILON'].sum() if 'PILON' in group.columns else 0
            
            # Handle R&D percentage - use the most recent value or average
            rd_percentage = group['R&D %'].iloc[-1] if 'R&D %' in group.columns else 0.0
            
            # Get date range for this employee
            start_date = group['Date'].min()
            end_date = group['Date'].max()
            period_count = len(group)
            
            # Create aggregated record
            aggregated_record = {
                'employee_name': employee_name,
                'gross_cost': total_gross,
                'er_ni_amount': total_er_ni,
                'er_pension_amount': total_er_pen,
                'bonus_amount': total_bonus,
                'pilon_amount': total_pilon,
                'rd_percentage': rd_percentage,
                'start_date': start_date,
                'end_date': end_date,
                'period_count': period_count,
                'description': f"Aggregated payroll data for {employee_name} ({period_count} periods)"
            }
            
            aggregated_data.append(aggregated_record)
        
        return pd.DataFrame(aggregated_data)

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
        
        # First aggregate the data by employee
        aggregated_data = self.aggregate_employee_data()
        
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
        
        # Process each aggregated employee record
        for index, row in aggregated_data.iterrows():
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
        Process a single line item from the aggregated data
        
        Args:
            row: Pandas Series representing an aggregated employee record
            employee_overrides: Employee-specific R&D percentages
            
        Returns:
            Dictionary containing processed line item data
        """
        # Extract basic information
        employee_name = row.get('employee_name', '')
        gross_cost = Decimal(str(row.get('gross_cost', 0)))
        er_ni_amount = Decimal(str(row.get('er_ni_amount', 0)))
        er_pension_amount = Decimal(str(row.get('er_pension_amount', 0)))
        bonus_amount = Decimal(str(row.get('bonus_amount', 0)))
        pilon_amount = Decimal(str(row.get('pilon_amount', 0)))
        cost_description = row.get('description', '')
        
        # Determine if this is EPW (externally provided worker)
        is_epw = row.get('is_epw', False)
        epw_connected = row.get('epw_connected', False)
        
        # Get R&D percentage - from data or override
        rd_percentage = self._get_rd_percentage(employee_name, employee_overrides, row.get('rd_percentage', 0.0))
        
        # Calculate qualifying amounts
        # Start with gross salary + ER NI + ER Pension (qualifying components)
        qualifying_base = gross_cost + er_ni_amount + er_pension_amount
        
        # Handle exclusions
        excluded_amount = Decimal('0')
        exclusion_reasons = []
        
        # PILON is always excluded
        if pilon_amount > 0:
            excluded_amount += pilon_amount
            exclusion_reasons.append(f"PILON: £{pilon_amount}")
        
        # Bonus might be excluded (configurable)
        if bonus_amount > 0:
            excluded_amount += bonus_amount
            exclusion_reasons.append(f"Bonus: £{bonus_amount}")
        
        # Total eligible amount (before R&D percentage)
        eligible_amount = qualifying_base
        
        # Apply R&D percentage
        qualifying_cost = eligible_amount * Decimal(str(rd_percentage))
        
        # Apply EPW cap if applicable
        if is_epw:
            epw_cap = eligible_amount * Decimal(str(self.rules['epw_cap_percentage']))
            qualifying_cost = min(qualifying_cost, epw_cap)
        
        # Determine if line item is excluded
        excluded = excluded_amount > 0
        exclusion_reason = "; ".join(exclusion_reasons) if exclusion_reasons else None
        
        return {
            'employee_name': employee_name,
            'description': cost_description,
            'gross_cost': gross_cost,
            'er_ni_amount': er_ni_amount,
            'er_pension_amount': er_pension_amount,
            'bonus_amount': bonus_amount,
            'pilon_amount': pilon_amount,
            'eligible_amount': eligible_amount,
            'excluded_amount': excluded_amount,
            'rd_percentage': rd_percentage,
            'qualifying_cost': qualifying_cost,
            'is_epw': is_epw,
            'epw_connected': epw_connected,
            'excluded': excluded,
            'exclusion_reason': exclusion_reason
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
    
    def _get_rd_percentage(self, employee_name: str, employee_overrides: Dict, data_rd_percentage: float = 0.0) -> float:
        """
        Get the R&D percentage for an employee
        
        Args:
            employee_name: Name of the employee
            employee_overrides: Employee-specific R&D percentages
            data_rd_percentage: R&D percentage from the data file
            
        Returns:
            R&D percentage as a float between 0 and 1
        """
        # Priority: 1. Manual override, 2. Data file, 3. Default
        if employee_name in employee_overrides:
            return employee_overrides[employee_name]
        
        # Use percentage from data file if available
        if data_rd_percentage > 0:
            return data_rd_percentage
        
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