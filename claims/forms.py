from django import forms
from django.forms import ModelForm
from .models import Claim, Employee, Mapping


class ClaimForm(ModelForm):
    """Form for creating and editing claims"""
    
    class Meta:
        model = Claim
        fields = ['name', 'description', 'period_start', 'period_end']
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date'}),
            'period_end': forms.DateInput(attrs={'type': 'date'}),
        }


class EmployeeForm(ModelForm):
    """Form for managing employee R&D percentages"""
    
    class Meta:
        model = Employee
        fields = ['name', 'email', 'default_rd_percentage', 'epw_connected']


class MappingForm(ModelForm):
    """Form for column mapping configuration"""
    
    class Meta:
        model = Mapping
        fields = ['name', 'description', 'mapping_config']


class FileUploadForm(forms.Form):
    """Form for uploading financial data files"""
    
    file = forms.FileField(
        label='Select file',
        help_text='Upload Excel (.xlsx) or CSV file'
    )
    file_type = forms.ChoiceField(
        choices=[
            ('payroll', 'Payroll Data'),
            ('trial_balance', 'Trial Balance'),
            ('timesheet', 'Timesheet Data'),
        ],
        label='File Type'
    ) 