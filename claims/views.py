from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum
from django.core.paginator import Paginator
import json
from datetime import datetime

from .models import (
    Claim, CostCategory, CostLineItem, GrantOrSubsidy, 
    NarrativeSection, Attachment, ReviewComment
)

@login_required
def claim_list(request):
    """List all claims for the current user"""
    claims = Claim.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(claims, 10)  # Show 10 claims per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_claims = claims.count()
    total_costs = claims.aggregate(total=Sum('total_costs'))['total'] or 0
    total_credits = claims.aggregate(total=Sum('credit_amount'))['total'] or 0
    completed_claims = claims.filter(status='completed').count()
    
    context = {
        'title': 'Claims',
        'claims': page_obj,
        'page_obj': page_obj,
        'total_claims': total_claims,
        'total_costs': total_costs,
        'total_credits': total_credits,
        'completed_claims': completed_claims,
    }
    return render(request, 'claims/claim_list.html', context)

@login_required
def claim_detail(request, pk):
    """View a specific claim"""
    claim = get_object_or_404(Claim, pk=pk, created_by=request.user)
    
    # Get related data
    cost_categories = claim.cost_categories.all()
    attachments = claim.attachments.all()
    narrative_sections = claim.narrative_sections.all()
    grants_subsidies = claim.grants_subsidies.all()
    comments = claim.comments.filter(is_resolved=False)
    
    context = {
        'title': 'Claim Details',
        'claim': claim,
        'claim_id': pk,
        'cost_categories': cost_categories,
        'attachments': attachments,
        'narrative_sections': narrative_sections,
        'grants_subsidies': grants_subsidies,
        'comments': comments,
    }
    return render(request, 'claims/claim_detail.html', context)

@login_required
def claim_create(request):
    """Create a new claim"""
    if request.method == 'POST':
        # Get form data
        claim_name = request.POST.get('claim_name', '')
        accounting_period = request.POST.get('accounting_period', '')
        company_name = request.POST.get('company_name', '')
        description = request.POST.get('description', '')
        
        # Validate required fields
        if not claim_name or not accounting_period or not company_name:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'claims/claim_create.html', {'title': 'Create New Claim'})
        
        # Create new claim
        claim = Claim.objects.create(
            name=claim_name,
            company=company_name,
            accounting_period=accounting_period,
            description=description,
            created_by=request.user,
            status='draft'
        )
        
        messages.success(request, f'Claim "{claim_name}" created successfully!')
        return redirect('claims:claim_detail', pk=claim.pk)
    
    context = {
        'title': 'Create New Claim',
    }
    return render(request, 'claims/claim_create.html', context)

@login_required
def claim_update(request, pk):
    """Update an existing claim"""
    claim = get_object_or_404(Claim, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        # Update claim fields
        claim.name = request.POST.get('claim_name', claim.name)
        claim.accounting_period = request.POST.get('accounting_period', claim.accounting_period)
        claim.company = request.POST.get('company_name', claim.company)
        claim.description = request.POST.get('description', claim.description)
        
        # Validate required fields
        if not claim.name or not claim.accounting_period or not claim.company:
            messages.error(request, 'Please fill in all required fields.')
        else:
            claim.save()
            messages.success(request, f'Claim "{claim.name}" updated successfully!')
            return redirect('claims:claim_detail', pk=pk)
    
    context = {
        'title': 'Update Claim',
        'claim': claim,
        'claim_id': pk,
    }
    return render(request, 'claims/claim_update.html', context)

@login_required
def claim_delete(request, pk):
    """Delete a claim"""
    claim = get_object_or_404(Claim, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        claim_name = claim.name
        claim.delete()
        messages.success(request, f'Claim "{claim_name}" deleted successfully!')
        return redirect('claims:claim_list')
    
    context = {
        'title': 'Delete Claim',
        'claim': claim,
        'claim_id': pk,
    }
    return render(request, 'claims/claim_delete.html', context)

@login_required
def upload_data(request, claim_id):
    """File upload view for specific claim"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        # Handle file upload
        uploaded_file = request.FILES.get('data_file')
        if uploaded_file:
            # Create attachment record
            attachment = Attachment.objects.create(
                claim=claim,
                filename=uploaded_file.name,
                original_filename=uploaded_file.name,
                file_path=uploaded_file,
                file_size=uploaded_file.size,
                file_type='payroll',  # Default to payroll, can be changed later
                uploaded_by=request.user
            )
            messages.success(request, 'File uploaded successfully!')
            return redirect('claims:column_mapping', claim_id=claim_id)
        else:
            messages.error(request, 'Please select a file to upload.')
    
    context = {
        'title': 'Upload File',
        'claim': claim,
        'claim_id': claim_id,
    }
    return render(request, 'claims/upload.html', context)

@login_required
def column_mapping(request, claim_id):
    """Column mapping view for specific claim"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        messages.success(request, 'Column mapping saved successfully!')
        return redirect('claims:claim_results', claim_id=claim_id)
    
    # Mock data for demonstration - in real implementation, this would analyze the uploaded file
    required_fields = [
        {'name': 'employee_name', 'label': 'Employee Name', 'description': 'Full name of employee'},
        {'name': 'gross_cost', 'label': 'Gross Cost', 'description': 'Gross cost amount'},
        {'name': 'period', 'label': 'Period', 'description': 'Accounting period'},
        {'name': 'description', 'label': 'Description', 'description': 'Cost description'},
    ]
    
    optional_fields = [
        {'name': 'department', 'label': 'Department', 'description': 'Employee department'},
        {'name': 'epw_flag', 'label': 'EPW Flag', 'description': 'Externally provided worker flag'},
    ]
    
    file_columns = ['Name', 'Gross Pay', 'Period', 'Job Title', 'Department', 'EPW']
    
    context = {
        'title': 'Column Mapping',
        'claim': claim,
        'claim_id': claim_id,
        'required_fields': required_fields,
        'optional_fields': optional_fields,
        'file_columns': file_columns,
        'sample_data': json.dumps({}),  # Empty for now
        'mapping_templates': json.dumps({}),  # Empty for now
    }
    return render(request, 'claims/mapping.html', context)

@login_required
def process_claim(request, claim_id):
    """Process claim data"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        # Update claim status
        claim.status = 'submitted'
        claim.save()
        
        messages.success(request, 'Claim processed successfully!')
        return redirect('claims:claim_results', claim_id=claim_id)
    
    context = {
        'title': 'Process Claim',
        'claim': claim,
        'claim_id': claim_id,
    }
    return render(request, 'claims/process.html', context)

@login_required
def claim_results(request, claim_id):
    """View claim results and calculations"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    # Get cost breakdown - group line items by type
    cost_categories = claim.cost_categories.all()
    
    # Get line items grouped by type for easy display
    line_items = claim.line_items.all().order_by('type', 'name')
    
    # Group line items by type
    items_by_type = {}
    for item in line_items:
        if item.type not in items_by_type:
            items_by_type[item.type] = []
        items_by_type[item.type].append(item)
    
    context = {
        'title': 'Claim Results',
        'claim': claim,
        'claim_id': claim_id,
        'cost_categories': cost_categories,
        'line_items': line_items,
        'items_by_type': items_by_type,
    }
    return render(request, 'claims/results.html', context)

@login_required
def claim_narrative(request, claim_id):
    """Manage claim narrative sections"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        # Save narrative sections
        for question in ['scientific_advance', 'technical_uncertainty', 'r_and_d_activities']:
            response = request.POST.get(f'narrative_{question}')
            if response:
                narrative, created = NarrativeSection.objects.get_or_create(
                    claim=claim,
                    question=question,
                    defaults={'response': response}
                )
                if not created:
                    narrative.response = response
                    narrative.save()
        
        messages.success(request, 'Narrative sections saved successfully!')
        return redirect('claims:claim_detail', pk=claim_id)
    
    # Get existing narrative sections
    narratives = {n.question: n.response for n in claim.narrative_sections.all()}
    
    context = {
        'title': 'Claim Narrative',
        'claim': claim,
        'claim_id': claim_id,
        'narratives': narratives,
    }
    return render(request, 'claims/narrative.html', context)

@login_required
def export_claim(request, claim_id):
    """Export claim data and generate CT600L"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    context = {
        'title': 'Export Claim',
        'claim': claim,
        'claim_id': claim_id,
    }
    return render(request, 'claims/export.html', context)

@login_required
def employee_list(request, claim_id):
    """List employees for a specific claim"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    # Get all staff line items
    line_items = claim.line_items.filter(type='staff').order_by('name')
    
    context = {
        'title': 'Employees',
        'claim': claim,
        'claim_id': claim_id,
        'line_items': line_items,
    }
    return render(request, 'claims/employee_list.html', context)

@login_required
def employee_add(request, claim_id):
    """Add employee to a claim"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        # This would create a new cost line item for the employee
        messages.success(request, 'Employee added successfully!')
        return redirect('claims:employee_list', claim_id=claim_id)
    
    context = {
        'title': 'Add Employee',
        'claim': claim,
        'claim_id': claim_id,
    }
    return render(request, 'claims/employee_add.html', context)

@login_required
def employee_edit(request, claim_id, employee_id):
    """Edit employee information"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    line_item = get_object_or_404(CostLineItem, pk=employee_id, claim=claim)
    
    if request.method == 'POST':
        # Update line item
        line_item.name = request.POST.get('employee_name', line_item.name)
        line_item.role = request.POST.get('role', line_item.role)
        line_item.gross_amount = request.POST.get('gross_amount', line_item.gross_amount)
        line_item.r_and_d_percentage = request.POST.get('r_and_d_percentage', line_item.r_and_d_percentage)
        line_item.save()
        
        messages.success(request, 'Employee information updated successfully!')
        return redirect('claims:employee_list', claim_id=claim_id)
    
    context = {
        'title': 'Edit Employee',
        'claim': claim,
        'claim_id': claim_id,
        'line_item': line_item,
    }
    return render(request, 'claims/employee_edit.html', context)

@login_required
def mapping_list(request):
    """List all column mappings"""
    # This would show saved mapping templates
    mappings = []  # Placeholder - would come from a mapping template model
    
    context = {
        'title': 'Column Mappings',
        'mappings': mappings,
    }
    return render(request, 'claims/mapping_list.html', context)

@login_required
def mapping_create(request):
    """Create a new column mapping template"""
    if request.method == 'POST':
        messages.success(request, 'Column mapping template created successfully!')
        return redirect('claims:mapping_list')
    
    context = {
        'title': 'Create Column Mapping',
    }
    return render(request, 'claims/mapping_create.html', context)

@login_required
def mapping_detail(request, pk):
    """View a specific mapping template"""
    # mapping = get_object_or_404(MappingTemplate, pk=pk)  # Would use real model
    
    context = {
        'title': 'Mapping Details',
        'mapping': None,  # Placeholder
    }
    return render(request, 'claims/mapping_detail.html', context)

@login_required
def mapping_update(request, pk):
    """Update a mapping template"""
    # mapping = get_object_or_404(MappingTemplate, pk=pk)  # Would use real model
    
    if request.method == 'POST':
        messages.success(request, 'Mapping template updated successfully!')
        return redirect('claims:mapping_detail', pk=pk)
    
    context = {
        'title': 'Update Mapping',
        'mapping': None,  # Placeholder
    }
    return render(request, 'claims/mapping_update.html', context)

@login_required
def mapping_delete(request, pk):
    """Delete a mapping template"""
    # mapping = get_object_or_404(MappingTemplate, pk=pk)  # Would use real model
    
    if request.method == 'POST':
        messages.success(request, 'Mapping template deleted successfully!')
        return redirect('claims:mapping_list')
    
    context = {
        'title': 'Delete Mapping',
        'mapping': None,  # Placeholder
    }
    return render(request, 'claims/mapping_delete.html', context)

@login_required
@csrf_exempt
def save_mapping(request, claim_id):
    """Save column mapping via AJAX"""
    if request.method == 'POST':
        try:
            claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
            mapping_data = json.loads(request.body)
            
            # In a real implementation, this would save the mapping to the database
            # For now, just return success
            
            return JsonResponse({'success': True, 'message': 'Mapping saved successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def cost_category_detail(request, claim_id, category_id):
    """Detailed view of a specific cost category with all line items and calculations"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    category = get_object_or_404(CostCategory, pk=category_id, claim=claim)
    
    # Get all line items for this category type
    line_items = claim.line_items.filter(type=category.category).order_by('name')
    
    # Calculate category statistics
    total_items = line_items.count()
    included_items = line_items.filter(is_excluded=False)
    excluded_items = line_items.filter(is_excluded=True)
    epw_items = line_items.filter(type='epw')
    grant_funded_items = line_items.filter(grant_funded=True)
    
    # Calculate EPW restrictions using the new model methods
    epw_calculations = []
    for item in epw_items:
        restriction_info = item.get_restriction_info()
        epw_calculations.append({
            'item': item,
            'original_amount': restriction_info['original_amount'],
            'capped_amount': restriction_info['final_amount'],
            'restriction_applied': restriction_info['has_restriction'],
            'restriction_rate': restriction_info['restriction_type'] or 'No cap',
            'reduction_amount': restriction_info['restriction_amount'],
            'connection_status': item.get_connection_status()
        })
    
    # Calculate totals
    total_gross = sum(item.gross_amount for item in line_items)
    total_eligible = sum(item.eligible_amount for item in included_items)
    total_excluded = sum(item.gross_amount for item in excluded_items)
    
    context = {
        'title': f'{category.get_category_display()} - Details',
        'claim': claim,
        'category': category,
        'line_items': line_items,
        'included_items': included_items,
        'excluded_items': excluded_items,
        'epw_items': epw_items,
        'grant_funded_items': grant_funded_items,
        'epw_calculations': epw_calculations,
        'total_items': total_items,
        'total_gross': total_gross,
        'total_eligible': total_eligible,
        'total_excluded': total_excluded,
        'stats': {
            'included_count': included_items.count(),
            'excluded_count': excluded_items.count(),
            'epw_count': epw_items.count(),
            'grant_funded_count': grant_funded_items.count(),
        }
    }
    
    return render(request, 'claims/cost_category_detail.html', context)
