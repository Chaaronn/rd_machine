import yaml
import os
from django.conf import settings
from typing import Dict, List, Optional, Any


class FormConfigManager:
    """Manages the loading and parsing of form configuration from YAML files"""
    
    def __init__(self):
        self.config_path = os.path.join(settings.BASE_DIR, 'config', 'category_form_config.yaml')
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load the YAML configuration file"""
        if self._config is None:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    self._config = yaml.safe_load(file)
            except FileNotFoundError:
                # Return default configuration if file doesn't exist
                self._config = self._get_default_config()
            except yaml.YAMLError as e:
                print(f"Error parsing YAML config: {e}")
                self._config = self._get_default_config()
        
        return self._config
    
    def get_category_config(self, category_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific category type"""
        config = self.load_config()
        return config.get('categories', {}).get(category_type)
    
    def get_all_categories(self) -> Dict[str, Any]:
        """Get all category configurations"""
        config = self.load_config()
        return config.get('categories', {})
    
    def get_field_config(self, category_type: str, field_name: str) -> Optional[Dict[str, str]]:
        """Get configuration for a specific field in a category"""
        category_config = self.get_category_config(category_type)
        if not category_config:
            return None
        
        return {
            'label': category_config.get('field_labels', {}).get(field_name, field_name.title()),
            'help': category_config.get('field_help', {}).get(field_name, ''),
            'required': field_name in category_config.get('required_fields', []),
            'optional': field_name in category_config.get('optional_fields', [])
        }
    
    def get_required_fields(self, category_type: str) -> List[str]:
        """Get list of required fields for a category"""
        category_config = self.get_category_config(category_type)
        return category_config.get('required_fields', []) if category_config else []
    
    def get_optional_fields(self, category_type: str) -> List[str]:
        """Get list of optional fields for a category"""
        category_config = self.get_category_config(category_type)
        return category_config.get('optional_fields', []) if category_config else []
    
    def get_all_fields(self, category_type: str) -> List[str]:
        """Get all fields (required + optional) for a category"""
        category_config = self.get_category_config(category_type)
        if not category_config:
            return []
        
        required = category_config.get('required_fields', [])
        optional = category_config.get('optional_fields', [])
        return required + optional
    
    def get_display_name(self, category_type: str) -> str:
        """Get display name for a category"""
        category_config = self.get_category_config(category_type)
        return category_config.get('display_name', category_type.title()) if category_config else category_type.title()
    
    def get_description(self, category_type: str) -> str:
        """Get description for a category"""
        category_config = self.get_category_config(category_type)
        return category_config.get('description', '') if category_config else ''
    
    def is_field_visible(self, category_type: str, field_name: str) -> bool:
        """Check if a field should be visible for a category"""
        all_fields = self.get_all_fields(category_type)
        return field_name in all_fields
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if YAML file is not found"""
        return {
            'categories': {
                'staff': {
                    'display_name': 'Staff',
                    'description': 'Employee costs',
                    'required_fields': ['name', 'gross_amount', 'r_and_d_percentage'],
                    'optional_fields': ['role', 'r_and_d_activity', 'cost_date', 'connected', 'grant_funded', 'grant_source', 'is_excluded', 'exclusion_reason', 'notes'],
                    'field_labels': {
                        'name': 'Employee Name',
                        'role': 'Job Title',
                        'gross_amount': 'Gross Salary',
                        'r_and_d_percentage': 'R&D Time %',
                        'r_and_d_activity': 'R&D Activities'
                    },
                    'field_help': {
                        'name': 'Full name of the employee',
                        'role': 'Job title or position',
                        'gross_amount': 'Total gross salary including benefits',
                        'r_and_d_percentage': 'Percentage of time spent on R&D activities',
                        'r_and_d_activity': 'Description of R&D work performed'
                    }
                },
                'epw': {
                    'display_name': 'Externally Provided Worker',
                    'description': 'External workers provided by third-party companies',
                    'required_fields': ['name', 'company_name', 'gross_amount', 'r_and_d_percentage', 'connected'],
                    'optional_fields': ['role', 'r_and_d_activity', 'cost_date', 'grant_funded', 'grant_source', 'is_excluded', 'exclusion_reason', 'notes'],
                    'field_labels': {
                        'name': 'Worker Name',
                        'company_name': 'Provider Company',
                        'role': 'Service Description',
                        'gross_amount': 'Service Cost',
                        'r_and_d_percentage': 'R&D Time %',
                        'connected': 'Connected Provider'
                    },
                    'field_help': {
                        'name': 'Name of the external worker',
                        'company_name': 'Name of the company providing the worker',
                        'role': 'Description of services provided',
                        'gross_amount': 'Total cost of the service',
                        'r_and_d_percentage': 'Percentage of time spent on R&D activities',
                        'connected': 'Check if the provider is connected (affects EPW restrictions)'
                    }
                }
            }
        }


# Global instance for easy access
form_config = FormConfigManager() 