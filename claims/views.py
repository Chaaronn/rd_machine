from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum
from django.core.paginator import Paginator
import json
import os
import pandas as pd
from datetime import datetime
from decimal import Decimal

from .models import (
    Claim, CostCategory, CostLineItem, GrantOrSubsidy, 
    NarrativeSection, Attachment, ReviewComment
)
from .utils.form_config import form_config

def _save_processed_line_items(claim, results, file_type='staff'):
    """
    Save processed line items from RDProcessor results to the database
    
    Args:
        claim: The Claim instance
        results: Results dictionary from RDProcessor.calculate_rd_costs()
        file_type: The file type/category selected during upload
    """
    print(f"DEBUG: _save_processed_line_items called with {len(results.get('line_items', []))} items")
    
    # Clear existing line items for this claim (in case of reprocessing)
    claim.line_items.all().delete()
    
    # Create line items from processed results
    for i, item_data in enumerate(results.get('line_items', [])):
        print(f"DEBUG: Processing item {i}: {item_data}")
        try:
            # Determine the type based on EPW flag (for backward compatibility) or use file type
            if item_data.get('is_epw', False):
                item_type = 'epw'
            else:
                # Use the file type from the upload to determine the item type
                item_type = file_type
            
            # Build description with breakdown
            description_parts = [item_data.get('description', '')]
            if item_data.get('er_ni_amount', 0) > 0:
                description_parts.append(f"ER NI: £{item_data.get('er_ni_amount', 0)}")
            if item_data.get('er_pension_amount', 0) > 0:
                description_parts.append(f"ER Pension: £{item_data.get('er_pension_amount', 0)}")
            if item_data.get('bonus_amount', 0) > 0:
                description_parts.append(f"Bonus: £{item_data.get('bonus_amount', 0)} (excluded)")
            if item_data.get('pilon_amount', 0) > 0:
                description_parts.append(f"PILON: £{item_data.get('pilon_amount', 0)} (excluded)")
            
            full_description = " | ".join(description_parts)
            
            # Store individual amounts in tags for editing (store all amounts, even 0)
            tags_data = {}
            for field_name in ['er_ni_amount', 'er_pension_amount', 'bonus_amount', 'pilon_amount']:
                value = item_data.get(field_name, 0)
                tags_data[field_name] = float(value)
                print(f"DEBUG: Storing {field_name} = {value} in tags")
            
            print(f"DEBUG: Final tags_data = {tags_data}")
            
            # Create the line item
            line_item = CostLineItem.objects.create(
                claim=claim,
                name=item_data.get('employee_name', 'Unknown'),
                type=item_type,
                r_and_d_activity=full_description,
                gross_amount=item_data.get('gross_cost', Decimal('0')),
                r_and_d_percentage=Decimal(str(item_data.get('rd_percentage', 1.0) * 100)),  # Convert to percentage
                eligible_amount=item_data.get('qualifying_cost', Decimal('0')),
                is_excluded=item_data.get('excluded', False),
                exclusion_reason=item_data.get('exclusion_reason', ''),
                connected=item_data.get('epw_connected', False),
                tags=tags_data,
                uploaded_by=claim.created_by,
            )
            print(f"DEBUG: Created line item: {line_item.name} - Gross: £{line_item.gross_amount}, Qualifying: £{line_item.eligible_amount}")
            
        except Exception as e:
            # Log error but continue processing other items
            print(f"Error creating line item: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Create or update cost categories summary
    _update_cost_categories(claim, results)

def _update_cost_categories(claim, results):
    """
    Update cost categories summary for the claim
    
    Args:
        claim: The Claim instance
        results: Results dictionary from RDProcessor.calculate_rd_costs()
    """
    # Clear existing cost categories
    claim.cost_categories.all().delete()
    
    # Create staff costs category if there are staff items
    staff_items = [item for item in results.get('line_items', []) if not item.get('is_epw', False)]
    if staff_items:
        staff_total = sum(item.get('qualifying_cost', Decimal('0')) for item in staff_items)
        CostCategory.objects.create(
            claim=claim,
            category='staff',
            total_cost=staff_total,
            eligible_cost=staff_total,
            description='Staff costs processed from uploaded data'
        )
    
    # Create EPW costs category if there are EPW items
    epw_items = [item for item in results.get('line_items', []) if item.get('is_epw', False)]
    if epw_items:
        epw_total = sum(item.get('qualifying_cost', Decimal('0')) for item in epw_items)
        CostCategory.objects.create(
            claim=claim,
            category='epw',
            total_cost=epw_total,
            eligible_cost=epw_total,
            description='EPW costs processed from uploaded data'
        )
    
    # Update claim totals
    claim.total_costs = results.get('total_costs', Decimal('0'))
    claim.qualifying_expenditure = results.get('total_qualifying_expenditure', Decimal('0'))
    claim.save()

def _recalculate_claim_totals(claim):
    """
    Recalculate claim totals and cost categories from existing line items
    
    Args:
        claim: The Claim instance
    """
    # Get all line items for this claim
    line_items = claim.line_items.all()
    
    # Clear existing cost categories
    claim.cost_categories.all().delete()
    
    # Group line items by type
    staff_items = line_items.filter(type='staff')
    epw_items = line_items.filter(type='epw')
    other_items = line_items.exclude(type__in=['staff', 'epw'])
    
    # Create staff costs category if there are staff items
    if staff_items.exists():
        staff_total = sum(item.gross_amount for item in staff_items)
        staff_eligible = sum(item.eligible_amount for item in staff_items if not item.is_excluded)
        CostCategory.objects.create(
            claim=claim,
            category='staff',
            total_cost=staff_total,
            eligible_cost=staff_eligible,
            description='Staff costs'
        )
    
    # Create EPW costs category if there are EPW items
    if epw_items.exists():
        epw_total = sum(item.gross_amount for item in epw_items)
        epw_eligible = sum(item.eligible_amount for item in epw_items if not item.is_excluded)
        CostCategory.objects.create(
            claim=claim,
            category='epw',
            total_cost=epw_total,
            eligible_cost=epw_eligible,
            description='EPW costs'
        )
    
    # Create other costs category if there are other items
    if other_items.exists():
        other_total = sum(item.gross_amount for item in other_items)
        other_eligible = sum(item.eligible_amount for item in other_items if not item.is_excluded)
        CostCategory.objects.create(
            claim=claim,
            category='other',
            total_cost=other_total,
            eligible_cost=other_eligible,
            description='Other costs'
        )
    
    # Update claim totals
    claim.total_costs = sum(item.gross_amount for item in line_items)
    claim.qualifying_expenditure = sum(item.eligible_amount for item in line_items if not item.is_excluded)
    claim.save()

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
        accounting_period_start = request.POST.get('accounting_period_start', '')
        accounting_period_end = request.POST.get('accounting_period_end', '')
        company_name = request.POST.get('company_name', '')
        description = request.POST.get('description', '')
        
        # Validate required fields
        if not claim_name or not accounting_period_start or not accounting_period_end or not company_name:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'claims/claim_create.html', {'title': 'Create New Claim'})
        
        # Validate dates
        try:
            start_date = datetime.strptime(accounting_period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(accounting_period_end, '%Y-%m-%d').date()

            # TODO: Add extended period detection
            # Could maybe be useful to add an extended flag to the model
            
            if start_date >= end_date:
                messages.error(request, 'End date must be after start date.')
                return render(request, 'claims/claim_create.html', {'title': 'Create New Claim'})

            # TODO: Add leap year handling
            # TODO: Fix this lol, doesn't work.
            '''if abs((end_date - start_date).days) <= 366:
                messages.error(request, 'Accounting Period must be at least 12 months.')
                return render(request, 'claims/claim_create.html', {'title': 'Create New Claim'})'''
            
            
        except ValueError:
            messages.error(request, 'Please enter valid dates.')
            return render(request, 'claims/claim_create.html', {'title': 'Create New Claim'})
        
        # Create new claim
        claim = Claim.objects.create(
            name=claim_name,
            company=company_name,
            accounting_period_start=start_date,
            accounting_period_end=end_date,
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
        # Get form data
        claim_name = request.POST.get('claim_name', claim.name)
        accounting_period_start = request.POST.get('accounting_period_start', '')
        accounting_period_end = request.POST.get('accounting_period_end', '')
        company_name = request.POST.get('company_name', claim.company)
        description = request.POST.get('description', claim.description)
        
        # Validate required fields
        if not claim_name or not accounting_period_start or not accounting_period_end or not company_name:
            messages.error(request, 'Please fill in all required fields.')
        else:
            # Validate dates
            try:
                start_date = datetime.strptime(accounting_period_start, '%Y-%m-%d').date()
                end_date = datetime.strptime(accounting_period_end, '%Y-%m-%d').date()
                
                if start_date >= end_date:
                    messages.error(request, 'End date must be after start date.')
                
                if abs((end_date - start_date).days) < 365:
                    messages.error(request, 'Accounting Period must be at least 12 months.')
                    return render(request, 'claims/claim_update.html', {'title': 'Update Claim'})
                
                else:
                    # Update claim fields
                    claim.name = claim_name
                    claim.accounting_period_start = start_date
                    claim.accounting_period_end = end_date
                    claim.company = company_name
                    claim.description = description
                    claim.save()
                    
                    messages.success(request, f'Claim "{claim.name}" updated successfully!')
                    return redirect('claims:claim_detail', pk=pk)
            except ValueError:
                messages.error(request, 'Please enter valid dates.')
    
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
        file_type = request.POST.get('file_type', 'other')
        
        if uploaded_file and file_type:
            # Validate file extension
            allowed_extensions = ['.xlsx', '.csv']
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                messages.error(request, f'Unsupported file format. Please upload Excel (.xlsx) or CSV (.csv) files only.')
                return render(request, 'claims/upload.html', {
                    'title': 'Upload File',
                    'claim': claim,
                    'claim_id': claim_id,
                })
            
            # Validate file size (10MB limit)
            max_file_size = 10 * 1024 * 1024  # 10MB in bytes
            if uploaded_file.size > max_file_size:
                messages.error(request, 'File is too large. Maximum file size is 10MB.')
                return render(request, 'claims/upload.html', {
                    'title': 'Upload File',
                    'claim': claim,
                    'claim_id': claim_id,
                })
            
            # Create attachment record
            attachment = Attachment.objects.create(
                claim=claim,
                filename=uploaded_file.name,
                original_filename=uploaded_file.name,
                file_path=uploaded_file,
                file_size=uploaded_file.size,
                file_type=file_type,
                uploaded_by=request.user
            )
            messages.success(request, 'File uploaded successfully!')
            return redirect('claims:column_mapping', claim_id=claim_id)
        else:
            if not uploaded_file:
                messages.error(request, 'Please select a file to upload.')
            if not file_type:
                messages.error(request, 'Please select a file type.')
    
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
    
    # Get the most recent attachment for this claim
    latest_attachment = claim.attachments.order_by('-uploaded_at').first()
    if not latest_attachment:
        messages.error(request, 'No file uploaded for this claim. Please upload a file first.')
        return redirect('claims:upload_data', claim_id=claim_id)
    
    if request.method == 'POST':
        # Get the mapping data from form
        mapping_data = {}
        for key, value in request.POST.items():
            if key.startswith('mapping_') and value:
                field_name = key.replace('mapping_', '')
                mapping_data[field_name] = value
        
        # Process the file with mapping
        try:
            from .logic.processor import RDProcessor
            
            processor = RDProcessor()
            file_path = latest_attachment.file_path.path
            
            # Debug: Print mapping data
            print(f"DEBUG: Mapping data: {mapping_data}")
            
            # Load the file
            if processor.load_data(file_path, latest_attachment.file_type):
                print(f"DEBUG: File loaded successfully. Shape: {processor.data.shape}")
                print(f"DEBUG: Columns: {processor.data.columns.tolist()}")
                print(f"DEBUG: First few rows:\n{processor.data.head()}")
                
                # Apply the column mapping
                if processor.apply_column_mapping(mapping_data):
                    print(f"DEBUG: Column mapping applied. New columns: {processor.data.columns.tolist()}")
                    print(f"DEBUG: Data after mapping:\n{processor.data.head()}")
                    
                    # Calculate R&D costs
                    results = processor.calculate_rd_costs()
                    
                    print(f"DEBUG: Results: {results}")
                    print(f"DEBUG: Number of line items: {len(results.get('line_items', []))}")
                    
                    # Save processed data as line items
                    _save_processed_line_items(claim, results, latest_attachment.file_type)
                    
                    # Update claim status
                    claim.status = 'processing'
                    claim.save()
                    
                    messages.success(request, 'File processed successfully!')
                    return redirect('claims:claim_results', claim_id=claim_id)
                else:
                    messages.error(request, 'Failed to apply column mapping.')
            else:
                messages.error(request, 'Failed to load file data.')
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            import traceback
            traceback.print_exc()
    
    # Read the uploaded file to extract column names
    try:
        file_path = latest_attachment.file_path.path
        
        # Validate file exists and is readable
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size (basic validation)
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty")
        
        # Try to read the file based on extension
        if file_path.lower().endswith('.xlsx'):
            try:
                df = pd.read_excel(file_path, engine='openpyxl', nrows=5)
            except Exception as excel_error:
                # If Excel reading fails, provide more specific error
                if "not a zip file" in str(excel_error).lower():
                    raise ValueError("File appears to be corrupted or not a valid Excel file. Please check the file format.")
                else:
                    raise ValueError(f"Cannot read Excel file: {excel_error}")
        elif file_path.lower().endswith('.csv'):
            try:
                df = pd.read_csv(file_path, nrows=5)
            except Exception as csv_error:
                # Try different encodings for CSV
                try:
                    df = pd.read_csv(file_path, encoding='latin-1', nrows=5)
                except:
                    raise ValueError(f"Cannot read CSV file: {csv_error}")
        else:
            raise ValueError("Unsupported file format. Please upload an Excel (.xlsx) or CSV (.csv) file.")
        
        file_columns = df.columns.tolist()
        sample_data = df.head(3).to_dict('records')  # First 3 rows as sample
        
    except Exception as e:
        messages.error(request, f'Error reading file: {str(e)}')
        file_columns = []
        sample_data = []

    # Map file types to YAML categories (now direct mapping since categories match)
    file_type_to_category = {
        'staff': 'staff',
        'subcontractor': 'other',
        'epw': 'staff',  # EPWs use staff category fields
        'software': 'other',
        'cloud': 'other',
        'consumables': 'other'
    }
    
    # Get the category based on file type
    file_type = latest_attachment.file_type
    category = file_type_to_category.get(file_type, 'other')
    
    # Load form configuration from YAML
    required_field_names = form_config.get_required_fields(category)
    optional_field_names = form_config.get_optional_fields(category)
    
    # Build required fields list with labels and descriptions
    required_fields = []
    for field_name in required_field_names:
        field_config = form_config.get_field_config(category, field_name)
        if field_config:
            required_fields.append({
                'name': field_name,
                'label': field_config['label'],
                'description': field_config['help']
            })
    
    # Build optional fields list with labels and descriptions
    optional_fields = []
    for field_name in optional_field_names:
        field_config = form_config.get_field_config(category, field_name)
        if field_config:
            optional_fields.append({
                'name': field_name,
                'label': field_config['label'],
                'description': field_config['help']
            })
    
    context = {
        'title': 'Column Mapping',
        'claim': claim,
        'claim_id': claim_id,
        'required_fields': required_fields,
        'optional_fields': optional_fields,
        'file_columns': file_columns,
        'sample_data': json.dumps(sample_data),
        'uploaded_file': latest_attachment,
        'row_count': len(df) if 'df' in locals() else 0,
    }
    return render(request, 'claims/mapping.html', context)

@login_required
def process_claim(request, claim_id):
    """Process claim data and calculate final totals"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        try:
            # Calculate final totals from line items
            line_items = claim.line_items.all()
            
            if not line_items.exists():
                messages.error(request, 'No line items found. Please upload and process data first.')
                return redirect('claims:column_mapping', claim_id=claim_id)
            
            # Calculate totals
            total_costs = sum(item.gross_amount for item in line_items)
            qualifying_expenditure = sum(item.eligible_amount for item in line_items if not item.is_excluded)
            
            # Apply NIC uplift to staff costs (13.8% as per UK regulations)
            staff_costs = sum(item.eligible_amount for item in line_items 
                            if item.type == 'staff' and not item.is_excluded)
            nic_uplift = staff_costs * Decimal('0.138')
            
            # Calculate total qualifying expenditure including NIC uplift
            total_qualifying_with_nic = qualifying_expenditure + nic_uplift
            
            # Calculate R&D tax credit (assuming SME scheme - can be made configurable)
            # SME rate is typically 33% of qualifying expenditure
            rd_credit = total_qualifying_with_nic * Decimal('0.33')
            
            # Update claim with calculated values
            claim.total_costs = total_costs
            claim.qualifying_expenditure = total_qualifying_with_nic
            claim.credit_amount = rd_credit
            claim.status = 'submitted'
            claim.save()
            
            messages.success(request, 'Claim processed successfully!')
            return redirect('claims:claim_results', claim_id=claim_id)
            
        except Exception as e:
            messages.error(request, f'Error processing claim: {str(e)}')
    
    # Get summary data for display
    line_items = claim.line_items.all()
    total_items = line_items.count()
    excluded_items = line_items.filter(is_excluded=True).count()
    epw_items = line_items.filter(type='epw').count()  # Fix: use type field, not is_epw
    
    context = {
        'title': 'Process Claim',
        'claim': claim,
        'claim_id': claim_id,
        'total_items': total_items,
        'excluded_items': excluded_items,
        'epw_items': epw_items,
        'line_items': line_items[:10],  # Show first 10 items as preview
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
    
    # Debug: Print what we found
    print(f"DEBUG: claim_results - Found {line_items.count()} line items")
    print(f"DEBUG: cost_categories count: {cost_categories.count()}")
    print(f"DEBUG: items_by_type keys: {list(items_by_type.keys())}")
    for item_type, items in items_by_type.items():
        print(f"DEBUG: {item_type}: {len(items)} items")
    
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
    
    # TODO: This should be in reference to the consultant
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

    # TODO: This should be in reference to the consultant
    # TODO: Make a new method for this to add an item to any cost category
    
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

    # TODO: Again, just make this in reference to the consultant
    # TODO: Make a new method for this to edit an item to any cost category
    
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
    """Detailed view of a specific cost category showing raw data before aggregation"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    category = get_object_or_404(CostCategory, pk=category_id, claim=claim)
    
    # Get the aggregated line items for summary stats
    line_items = claim.line_items.filter(type=category.category).order_by('name')
    
    # Load the original raw data from the uploaded file
    raw_data_by_employee = {}
    latest_attachment = claim.attachments.order_by('-uploaded_at').first()
    
    if latest_attachment:
        try:
            from .logic.processor import RDProcessor
            import pandas as pd
            
            # Load original data
            processor = RDProcessor()
            file_path = latest_attachment.file_path.path
            
            if processor.load_data(file_path, latest_attachment.file_type):
                # Apply column mapping to get standard field names
                # Get the saved mapping from the session or reconstruct it
                mapping_data = {
                    'Date': 'Date',
                    'Name': 'Name', 
                    'Gross': 'Gross',
                    'ErNI': 'ErNI',
                    'ErPen': 'ErPen',
                    'Bonus': 'Bonus',
                    'PILON': 'PILON',
                    'R&D %': 'R&D %'
                }
                
                if processor.apply_column_mapping(mapping_data):
                    # Group raw data by employee
                    for employee_name, group in processor.data.groupby('Name'):
                        # Only include if this employee has a line item in this category
                        if line_items.filter(name=employee_name).exists():
                            employee_line_item = line_items.get(name=employee_name)
                            
                            # Convert group to list of dictionaries for easier template handling
                            periods = []
                            for _, row in group.iterrows():
                                rd_percentage_decimal = row.get('R&D %', 0)
                                rd_percentage_display = rd_percentage_decimal * 100  # Convert decimal to percentage for display
                                periods.append({
                                    'date': row.get('Date', ''),
                                    'gross': row.get('Gross', 0),
                                    'er_ni': row.get('ErNI', 0),
                                    'er_pen': row.get('ErPen', 0),
                                    'bonus': row.get('Bonus', 0),
                                    'pilon': row.get('PILON', 0),
                                    'rd_percentage': rd_percentage_display,
                                    'qualifying_base': row.get('Gross', 0) + row.get('ErNI', 0) + row.get('ErPen', 0),
                                    'qualifying_amount': (row.get('Gross', 0) + row.get('ErNI', 0) + row.get('ErPen', 0)) * rd_percentage_decimal
                                })
                            
                            # Calculate totals for this employee
                            total_gross = sum(p['gross'] for p in periods)
                            total_er_ni = sum(p['er_ni'] for p in periods)
                            total_er_pen = sum(p['er_pen'] for p in periods)
                            total_bonus = sum(p['bonus'] for p in periods)
                            total_pilon = sum(p['pilon'] for p in periods)
                            total_qualifying_base = sum(p['qualifying_base'] for p in periods)
                            total_qualifying_amount = sum(p['qualifying_amount'] for p in periods)
                            
                            raw_data_by_employee[employee_name] = {
                                'line_item': employee_line_item,
                                'periods': periods,
                                'period_count': len(periods),
                                'totals': {
                                    'gross': total_gross,
                                    'er_ni': total_er_ni,
                                    'er_pen': total_er_pen,
                                    'bonus': total_bonus,
                                    'pilon': total_pilon,
                                    'qualifying_base': total_qualifying_base,
                                    'qualifying_amount': total_qualifying_amount
                                }
                            }
                            
        except Exception as e:
            print(f"Error loading raw data: {e}")
            # Fall back to aggregated data if raw data can't be loaded
            pass
    
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
        'title': f'{category.get_category_display()} - Raw Data',
        'claim': claim,
        'category': category,
        'line_items': line_items,
        'raw_data_by_employee': raw_data_by_employee,
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

@login_required
def line_item_list(request, claim_id, category_type=None):
    """List line items for a specific claim, optionally filtered by category type"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    # Get line items, optionally filtered by category type
    line_items = claim.line_items.all()
    if category_type:
        line_items = line_items.filter(type=category_type)
    
    line_items = line_items.order_by('type', 'name')
    
    # Group line items by type for display
    items_by_type = {}
    for item in line_items:
        if item.type not in items_by_type:
            items_by_type[item.type] = []
        items_by_type[item.type].append(item)
    
    context = {
        'title': f'Line Items{f" - {category_type.title()}" if category_type else ""}',
        'claim': claim,
        'claim_id': claim_id,
        'line_items': line_items,
        'items_by_type': items_by_type,
        'category_type': category_type,
    }
    return render(request, 'claims/line_item_list.html', context)

@login_required
def line_item_add(request, claim_id, category_type=None):
    """Add a new line item to a claim"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '')
        item_type = request.POST.get('type', category_type or 'other')
        description = request.POST.get('description', '')
        gross_amount = request.POST.get('gross_amount', 0)
        r_and_d_percentage = request.POST.get('r_and_d_percentage', 100)
        
        # Validate required fields
        if not name or not gross_amount:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'claims/line_item_add.html', {
                'title': 'Add Line Item',
                'claim': claim,
                'claim_id': claim_id,
                'category_type': category_type,
            })
        
        try:
            # Create new line item
            line_item = CostLineItem.objects.create(
                claim=claim,
                name=name,
                type=item_type,
                description=description,
                gross_amount=float(gross_amount),
                r_and_d_percentage=int(r_and_d_percentage),
            )
            
            # Recalculate claim totals and cost categories after adding
            _recalculate_claim_totals(claim)
            
            messages.success(request, f'Line item "{name}" added successfully!')
            return redirect('claims:line_item_list', claim_id=claim_id)
            
        except ValueError:
            messages.error(request, 'Please enter valid numeric values.')
        except Exception as e:
            messages.error(request, f'Error creating line item: {str(e)}')
    
    context = {
        'title': f'Add Line Item{f" - {category_type.title()}" if category_type else ""}',
        'claim': claim,
        'claim_id': claim_id,
        'category_type': category_type,
        'category_choices': CostLineItem.TYPE_CHOICES,
    }
    return render(request, 'claims/line_item_add.html', context)

@login_required
def line_item_edit(request, claim_id, item_id):
    """Edit an existing line item"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    line_item = get_object_or_404(CostLineItem, pk=item_id, claim=claim)
    
    # Load form configuration based on line item type
    from .utils.form_config import FormConfigManager
    form_config_manager = FormConfigManager()
    
    # Map line item types to YAML categories
    type_to_category = {
        'staff': 'staff',
        'epw': 'staff',  # EPW uses staff category fields
        'subcontractor': 'other',
        'software': 'other',
        'cloud': 'other',
        'consumables': 'other',
        'equipment': 'other',
        'other': 'other'
    }
    
    # Get the category based on line item type
    category = type_to_category.get(line_item.type, 'other')
    
    # Load field configuration
    required_field_names = form_config_manager.get_required_fields(category)
    optional_field_names = form_config_manager.get_optional_fields(category)
    
    # Build field configuration for template
    available_fields = {}
    print(f"DEBUG: line_item.tags = {line_item.tags}")
    print(f"DEBUG: line_item.name = {line_item.name}")
    print(f"DEBUG: line_item.gross_amount = {line_item.gross_amount}")
    print(f"DEBUG: line_item.r_and_d_percentage = {line_item.r_and_d_percentage}")
    
    # Create mapping between YAML field names and actual stored data
    field_mapping = {
        'Date': 'cost_date',
        'Name': 'employee_name',
        'Gross': 'gross_amount',
        'ErNI': 'er_ni_amount',
        'ErPen': 'er_pension_amount',
        'Bonus': 'bonus_amount',
        'PILON': 'pilon_amount',
        'R&D %': 'rd_percentage',
        'employee_name': 'name',  # Direct mapping
        'gross_amount': 'gross_amount',  # Direct mapping
        'rd_percentage': 'r_and_d_percentage',  # Direct mapping
    }
    
    for field_name in required_field_names + optional_field_names:
        field_config = form_config_manager.get_field_config(category, field_name)
        if field_config:
            # Get value from line item or tags using mapping
            value = ''
            
            # Use mapping to find the actual field name
            actual_field_name = field_mapping.get(field_name, field_name)
            
            if actual_field_name == 'name':
                value = line_item.name
            elif actual_field_name == 'gross_amount':
                value = line_item.gross_amount
            elif actual_field_name == 'r_and_d_percentage':
                value = line_item.r_and_d_percentage
            elif actual_field_name == 'cost_date':
                value = line_item.cost_date
            elif actual_field_name in ['er_ni_amount', 'er_pension_amount', 'bonus_amount', 'pilon_amount']:
                # Get from tags JSON field, default to 0 if not found
                if isinstance(line_item.tags, dict):
                    value = line_item.tags.get(actual_field_name, 0)
                else:
                    value = 0
                # Convert to float for form display
                try:
                    value = float(value) if value else 0
                except (ValueError, TypeError):
                    value = 0
            elif hasattr(line_item, actual_field_name):
                value = getattr(line_item, actual_field_name, '')
            else:
                value = ''
            
            print(f"DEBUG: field_name = {field_name}, actual_field_name = {actual_field_name}, value = {value}")
            
            available_fields[field_name] = {
                'label': field_config['label'],
                'help': field_config['help'],
                'required': field_name in required_field_names,
                'value': value
            }
    
    if request.method == 'POST':
        # Get form data using the same field mapping
        name = request.POST.get('Name', request.POST.get('employee_name', line_item.name))
        item_type = request.POST.get('type', line_item.type)
        company_name = request.POST.get('company_name', line_item.company_name)
        role = request.POST.get('role', line_item.role)
        cost_date = request.POST.get('Date', line_item.cost_date)
        gross_amount = request.POST.get('Gross', request.POST.get('gross_amount', line_item.gross_amount))
        r_and_d_percentage = request.POST.get('R&D %', request.POST.get('rd_percentage', line_item.r_and_d_percentage))
        r_and_d_activity = request.POST.get('r_and_d_activity', line_item.r_and_d_activity)
        connected = request.POST.get('connected') == 'on'
        grant_funded = request.POST.get('grant_funded') == 'on'
        grant_source = request.POST.get('grant_source', line_item.grant_source)
        is_excluded = request.POST.get('is_excluded') == 'on'
        exclusion_reason = request.POST.get('exclusion_reason', line_item.exclusion_reason)
        notes = request.POST.get('notes', line_item.notes)
        
        # Get YAML-configured fields from the form and save to tags
        tags_data = dict(line_item.tags) if isinstance(line_item.tags, dict) else {}
        
        # Use the field mapping to save data correctly
        for field_name in required_field_names + optional_field_names:
            field_value = request.POST.get(field_name)
            if field_value:
                actual_field_name = field_mapping.get(field_name, field_name)
                
                # Save individual amounts to tags
                if actual_field_name in ['er_ni_amount', 'er_pension_amount', 'bonus_amount', 'pilon_amount']:
                    try:
                        tags_data[actual_field_name] = float(field_value)
                    except ValueError:
                        tags_data[actual_field_name] = 0
        
        # Validate required fields
        if not name or not gross_amount:
            messages.error(request, 'Please fill in all required fields.')
        else:
            try:
                # Update line item
                line_item.name = name
                line_item.type = item_type
                line_item.company_name = company_name
                line_item.role = role
                line_item.cost_date = cost_date if cost_date else None
                line_item.gross_amount = float(gross_amount)
                line_item.r_and_d_percentage = float(r_and_d_percentage)
                line_item.r_and_d_activity = r_and_d_activity
                line_item.connected = connected
                line_item.grant_funded = grant_funded
                line_item.grant_source = grant_source
                line_item.is_excluded = is_excluded
                line_item.exclusion_reason = exclusion_reason
                line_item.notes = notes
                line_item.tags = tags_data
                line_item.save()
                
                # Recalculate claim totals and cost categories after editing
                _recalculate_claim_totals(claim)
                
                messages.success(request, f'Line item "{name}" updated successfully!')
                return redirect('claims:line_item_list', claim_id=claim_id)
                
            except ValueError:
                messages.error(request, 'Please enter valid numeric values.')
            except Exception as e:
                messages.error(request, f'Error updating line item: {str(e)}')
    
    context = {
        'title': 'Edit Line Item',
        'claim': claim,
        'claim_id': claim_id,
        'line_item': line_item,
        'category_choices': CostLineItem.TYPE_CHOICES,
        'available_fields': available_fields,
        'category': category,
        'required_field_names': required_field_names,
        'optional_field_names': optional_field_names,
    }
    return render(request, 'claims/line_item_edit.html', context)

@login_required
def line_item_delete(request, claim_id, item_id):
    """Delete a line item"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    line_item = get_object_or_404(CostLineItem, pk=item_id, claim=claim)
    
    if request.method == 'POST':
        line_item_name = line_item.name
        line_item.delete()
        
        # Recalculate claim totals and cost categories after deletion
        _recalculate_claim_totals(claim)
        
        messages.success(request, f'Line item "{line_item_name}" deleted successfully!')
        return redirect('claims:line_item_list', claim_id=claim_id)
    
    context = {
        'title': 'Delete Line Item',
        'claim': claim,
        'claim_id': claim_id,
        'line_item': line_item,
    }
    return render(request, 'claims/line_item_delete.html', context)

@login_required
def debug_line_items(request, claim_id):
    """Debug view to check line items in database"""
    claim = get_object_or_404(Claim, pk=claim_id, created_by=request.user)
    
    print(f"DEBUG: Checking line items for claim {claim_id}")
    line_items = claim.line_items.all()
    print(f"DEBUG: Found {line_items.count()} line items")
    
    for item in line_items:
        print(f"DEBUG: Line item - Name: {item.name}, Type: {item.type}, Gross: £{item.gross_amount}, Eligible: £{item.eligible_amount}")
    
    cost_categories = claim.cost_categories.all()
    print(f"DEBUG: Found {cost_categories.count()} cost categories")
    
    for category in cost_categories:
        print(f"DEBUG: Cost category - {category.category}: Total: £{category.total_cost}, Eligible: £{category.eligible_cost}")
    
    return JsonResponse({
        'line_items_count': line_items.count(),
        'cost_categories_count': cost_categories.count(),
        'line_items': [
            {
                'name': item.name,
                'type': item.type,
                'gross_amount': float(item.gross_amount),
                'eligible_amount': float(item.eligible_amount),
            } for item in line_items
        ],
        'cost_categories': [
            {
                'category': category.category,
                'total_cost': float(category.total_cost),
                'eligible_cost': float(category.eligible_cost),
            } for category in cost_categories
        ]
    })
