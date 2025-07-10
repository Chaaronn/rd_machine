from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Claim, CostCategory, CostLineItem, GrantOrSubsidy, 
    NarrativeSection, Attachment, ReviewComment
)


class CostCategoryInline(admin.TabularInline):
    """Inline admin for cost categories within claims"""
    model = CostCategory
    extra = 0
    fields = ('category', 'total_cost', 'eligible_cost', 'description')
    readonly_fields = ('created_at', 'updated_at')


class CostLineItemInline(admin.TabularInline):
    """Inline admin for cost line items within claims"""
    model = CostLineItem
    extra = 0
    fields = (
        'type', 'name', 'company_name', 'connected', 'gross_amount', 
        'r_and_d_percentage', 'eligible_amount', 'is_excluded'
    )
    readonly_fields = ('eligible_amount',)


class AttachmentInline(admin.TabularInline):
    """Inline admin for attachments within claims"""
    model = Attachment
    extra = 0
    fields = ('original_filename', 'file_type', 'description', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_by', 'uploaded_at', 'file_size')


class NarrativeSectionInline(admin.StackedInline):
    """Inline admin for narrative sections within claims"""
    model = NarrativeSection
    extra = 0
    fields = ('question', 'custom_question', 'response')


class GrantOrSubsidyInline(admin.TabularInline):
    """Inline admin for grants/subsidies within claims"""
    model = GrantOrSubsidy
    extra = 0
    fields = ('source', 'amount', 'applies_to', 'impact_description')


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    """Admin interface for Claims"""
    list_display = (
        'name', 'company', 'get_accounting_period_display', 'status', 
        'total_costs_display', 'eligible_costs_display', 
        'credit_amount_display', 'created_by', 'created_at'
    )
    list_filter = ('status', 'accounting_period_start', 'accounting_period_end', 'created_at', 'created_by')
    search_fields = ('name', 'company', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'get_eligible_percentage')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'company', 'accounting_period_start', 'accounting_period_end', 'description', 'status')
        }),
        ('Financial Summary', {
            'fields': ('total_costs', 'eligible_costs', 'credit_amount', 'get_eligible_percentage'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CostCategoryInline, CostLineItemInline, AttachmentInline, NarrativeSectionInline, GrantOrSubsidyInline]
    
    def total_costs_display(self, obj):
        return f"£{obj.total_costs:,.2f}"
    total_costs_display.short_description = 'Total Costs'
    
    def eligible_costs_display(self, obj):
        return f"£{obj.eligible_costs:,.2f}"
    eligible_costs_display.short_description = 'Eligible Costs'
    
    def credit_amount_display(self, obj):
        return f"£{obj.credit_amount:,.2f}"
    credit_amount_display.short_description = 'Credit Amount'
    
    def get_eligible_percentage(self, obj):
        return f"{obj.get_eligible_percentage():.1f}%"
    get_eligible_percentage.short_description = 'Eligible %'


@admin.register(CostCategory)
class CostCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Cost Categories"""
    list_display = (
        'category', 'claim', 'total_cost_display', 
        'eligible_cost_display', 'get_eligible_percentage', 'created_at'
    )
    list_filter = ('category', 'claim__status', 'created_at')
    search_fields = ('claim__name', 'claim__company', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'get_eligible_percentage')
    
    fieldsets = (
        ('Category Information', {
            'fields': ('claim', 'category', 'description')
        }),
        ('Financial Data', {
            'fields': ('total_cost', 'eligible_cost', 'get_eligible_percentage')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_cost_display(self, obj):
        return f"£{obj.total_cost:,.2f}"
    total_cost_display.short_description = 'Total Cost'
    
    def eligible_cost_display(self, obj):
        return f"£{obj.eligible_cost:,.2f}"
    eligible_cost_display.short_description = 'Eligible Cost'


@admin.register(CostLineItem)
class CostLineItemAdmin(admin.ModelAdmin):
    """Admin interface for Cost Line Items"""
    list_display = (
        'name', 'type', 'claim', 'gross_amount_display', 
        'r_and_d_percentage', 'eligible_amount_display', 
        'is_excluded', 'grant_funded', 'get_connection_status', 'created_at'
    )
    list_filter = (
        'type', 'is_excluded', 'grant_funded', 
        'connected', 'created_at', 'claim__status'
    )
    search_fields = ('name', 'company_name', 'role', 'r_and_d_activity')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'eligible_amount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Item Information', {
            'fields': ('claim', 'type', 'name', 'company_name', 'role', 'r_and_d_activity')
        }),
        ('Connection & Restrictions', {
            'fields': ('connected',)
        }),
        ('Financial Data', {
            'fields': ('gross_amount', 'r_and_d_percentage', 'eligible_amount')
        }),
        ('Flags and Exclusions', {
            'fields': ('is_excluded', 'exclusion_reason', 'grant_funded', 'grant_source')
        }),
        ('Additional Information', {
            'fields': ('notes', 'tags'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def gross_amount_display(self, obj):
        return f"£{obj.gross_amount:,.2f}"
    gross_amount_display.short_description = 'Gross Amount'
    
    def eligible_amount_display(self, obj):
        return f"£{obj.eligible_amount:,.2f}"
    eligible_amount_display.short_description = 'Eligible Amount'


@admin.register(GrantOrSubsidy)
class GrantOrSubsidyAdmin(admin.ModelAdmin):
    """Admin interface for Grants or Subsidies"""
    list_display = ('source', 'claim', 'amount_display', 'applies_to', 'created_at')
    list_filter = ('applies_to', 'created_at', 'claim__status')
    search_fields = ('source', 'claim__name', 'claim__company', 'impact_description')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Grant/Subsidy Information', {
            'fields': ('claim', 'source', 'amount', 'applies_to')
        }),
        ('Application Details', {
            'fields': ('line_item', 'impact_description')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"£{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'


@admin.register(NarrativeSection)
class NarrativeSectionAdmin(admin.ModelAdmin):
    """Admin interface for Narrative Sections"""
    list_display = ('claim', 'question', 'response_preview', 'created_at')
    list_filter = ('question', 'created_at', 'claim__status')
    search_fields = ('claim__name', 'claim__company', 'response', 'custom_question')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Question Information', {
            'fields': ('claim', 'question', 'custom_question')
        }),
        ('Response', {
            'fields': ('response',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def response_preview(self, obj):
        return obj.response[:100] + "..." if len(obj.response) > 100 else obj.response
    response_preview.short_description = 'Response Preview'


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """Admin interface for Attachments"""
    list_display = (
        'original_filename', 'claim', 'file_type', 
        'file_size_display', 'uploaded_by', 'uploaded_at'
    )
    list_filter = ('file_type', 'uploaded_at', 'uploaded_by', 'claim__status')
    search_fields = ('original_filename', 'claim__name', 'claim__company', 'description')
    ordering = ('-uploaded_at',)
    readonly_fields = ('id', 'file_size', 'uploaded_at')
    
    fieldsets = (
        ('File Information', {
            'fields': ('claim', 'original_filename', 'file_path', 'file_type', 'description')
        }),
        ('Upload Details', {
            'fields': ('file_size', 'uploaded_by', 'uploaded_at')
        }),
        ('System Information', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = 'File Size'


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    """Admin interface for Review Comments"""
    list_display = (
        'comment_type', 'author', 'get_related_object_display', 
        'comment_preview', 'is_resolved', 'created_at'
    )
    list_filter = ('comment_type', 'is_resolved', 'created_at', 'author')
    search_fields = ('comment', 'author__username', 'claim__name')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Comment Information', {
            'fields': ('comment_type', 'claim', 'line_item', 'comment')
        }),
        ('Status', {
            'fields': ('is_resolved',)
        }),
        ('System Information', {
            'fields': ('id', 'author', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def comment_preview(self, obj):
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment Preview'
    
    def get_related_object_display(self, obj):
        """Display the related object this comment is about"""
        related_obj = obj.get_related_object()
        if related_obj:
            return str(related_obj)
        return "No related object"
    get_related_object_display.short_description = 'Related Object'


# Admin site customization
admin.site.site_header = 'R&D Machine Administration'
admin.site.site_title = 'R&D Machine Admin'
admin.site.index_title = 'Welcome to R&D Machine Administration'
