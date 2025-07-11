from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class Claim(models.Model):
    """Main claim model representing an R&D tax credit claim"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Descriptive name for the claim")
    company = models.CharField(max_length=200, help_text="Company name")

    # Date range for the accounting period
    # This allows for the calculation of period specific rates (e.g., 14.5% pre 1 April 2023)
    accounting_period_start = models.DateField(
        default=timezone.datetime(2024, 4, 1).date(),
        help_text="Start date of accounting period"
    )
    accounting_period_end = models.DateField(
        default=timezone.datetime(2025, 3, 31).date(),
        help_text="End date of accounting period"
    )

    

    description = models.TextField(blank=True, help_text="Brief description of R&D activities")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial fields
    total_costs = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total costs across all categories"
    )
    eligible_costs = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total eligible costs for R&D credit"
    )
    credit_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Calculated R&D tax credit amount"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # User relationship
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['company', 'accounting_period_start', 'accounting_period_end']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.company} ({self.accounting_period_start.year}-{self.accounting_period_end.year})"
    
    def get_eligible_percentage(self):
        """Calculate the percentage of eligible costs"""
        if self.total_costs > 0:
            return (self.eligible_costs / self.total_costs) * 100
        return 0
    
    def calculate_credit_amount(self):
        """Calculate R&D tax credit amount (26% of eligible costs for SMEs)"""
        return self.eligible_costs * 0.26
    
    def get_accounting_period_display(self):
        """Get formatted accounting period string"""
        return f"{self.accounting_period_start.year}-{self.accounting_period_end.year}"
    
    def get_r_and_d_rate(self):
        """Get the applicable R&D rate based on the accounting period"""
        # Rate changes from 1 April 2023
        rate_change_date = timezone.datetime(2023, 4, 1).date()
        

        # This doesn't work in legislation, it needs to account for if the date is between the range
        # Then, we will need to flag specific line items occuring before this date 
        # Basically, generating two sets of costs for pre/post

        # This should also return the additional deduciton
        # at either 1.3 or .86 depending on regime/dates/

        # This could also maybe handle the merged regime

        if self.accounting_period_start <= rate_change_date:
            return Decimal('0.145')  # 14.5%
        else:
            return Decimal('0.1')   # 10%

        
    
    def calculate_credit_amount_with_rate(self):
        """Calculate R&D tax credit amount using period-specific rate"""

        # Super basic for now. In future, this need to be expanded to use 
        # the additional deduciton/enhancment, or the lower of argument 

        rate = self.get_r_and_d_rate()
        
        # add_deduct - self.eligible_costs * add_deduct_rate

        return self.eligible_costs * rate


class CostCategory(models.Model):
    """Categories of costs within a claim"""
    
    CATEGORY_CHOICES = [
        ('staff', 'Staff Costs'),
        ('subcontractor', 'Subcontractor Costs'),
        ('epw', 'Externally Provided Workers'),
        ('software', 'Software Costs'),
        ('consumables', 'Consumables'),
        ('other', 'Other Costs'),               # This is placeholder, probs replace with cloud etc
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='cost_categories')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    eligible_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)]
    )
    description = models.TextField(blank=True, help_text="Optional summary or notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['claim', 'category']
        ordering = ['category']
        indexes = [
            models.Index(fields=['claim', 'category']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.claim.name}"
    
    def get_eligible_percentage(self):
        """Calculate the percentage of eligible costs in this category"""
        if self.total_cost > 0:
            return (self.eligible_cost / self.total_cost) * 100
        return 0


class CostLineItem(models.Model):
    """Individual cost items with cleaner type-based structure"""
    
    TYPE_CHOICES = [
        ('staff', 'Staff'),
        ('epw', 'Externally Provided Worker'),
        ('subcontractor', 'Subcontractor'),
        ('software', 'Software'),
        ('cloud', 'Cloud Services'),
        ('consumables', 'Consumables'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='line_items')
    
    # Type and connection
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, help_text="Type of cost item")
    connected = models.BooleanField(
        default=False, 
        help_text="Whether EPW/subcontractor is connected (affects restrictions)"
    )
    
    # Basic information
    name = models.CharField(max_length=200, help_text="Name of individual or supplier")
    company_name = models.CharField(max_length=200, blank=True, help_text="Company name for EPWs/subcontractors")
    role = models.CharField(max_length=200, blank=True, help_text="Job title/function/service description")
    r_and_d_activity = models.TextField(blank=True, help_text="Description of R&D work performed")

    # Date when the cost was incurred
    # This can be used in conjunction with rules on period rates
    cost_date = models.DateField(
        null=True, 
        blank=True, 
        help_text="Date when the cost was incurred (for period-specific calculations)"
    )

    
    # Financial fields

    # TODO: Make this a bit more dynamic, based on the cost category

    gross_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Original cost amount"
    )
    r_and_d_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100,
        help_text="Percentage attributable to R&D"
    )
    eligible_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Calculated eligible amount (after restrictions)"
    )
    
    # Exclusions and grants
    grant_funded = models.BooleanField(default=False, help_text="Funded by grant or subsidy")
    grant_source = models.CharField(max_length=200, blank=True, help_text="Source of grant funding")
    is_excluded = models.BooleanField(default=False, help_text="Excluded from R&D calculation")
    exclusion_reason = models.CharField(
        max_length=500, 
        blank=True, 
        help_text="Reason for exclusion (e.g., PILON, Bonus, Insufficient evidence)"
    )
    
    # Additional metadata
    tags = models.JSONField(default=list, blank=True, help_text="Tags like NIC uplift, capped, etc.")
    notes = models.TextField(blank=True, help_text="Freeform notes")
    
    # User and timestamps
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_line_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['type', 'name', 'created_at']
        indexes = [
            models.Index(fields=['claim', 'type']),
            models.Index(fields=['type', 'is_excluded']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()}) - {self.claim.name}"
    
    def save(self, *args, **kwargs):
        """Calculate eligible amount with EPW restrictions before saving"""
        if not self.is_excluded:
            # Basic calculation: gross_amount * r_and_d_percentage
            base_amount = (self.gross_amount * self.r_and_d_percentage) / 100
            
            # Apply EPW 65% cap for unconnected EPWs
            # TODO: Move this to a config file, just in case it changes in future
            if self.type == 'epw' and not self.connected:
                self.eligible_amount = base_amount * Decimal('0.65')
                if 'epw_capped' not in self.tags:
                    self.tags.append('epw_capped')
            else:
                self.eligible_amount = base_amount
                # Remove capped tag if no longer applicable
                if 'epw_capped' in self.tags:
                    self.tags.remove('epw_capped')
        else:
            self.eligible_amount = 0
        
        super().save(*args, **kwargs)
    
    def get_display_name(self):
        """Get appropriate display name"""
        return self.name
    
    def get_connection_status(self):
        """Get human-readable connection status"""
        if self.type in ['epw', 'subcontractor']:
            return 'Connected' if self.connected else 'Unconnected'
        return 'N/A'
    
    def get_restriction_info(self):
        """Get information about any restrictions applied"""
        if self.type == 'epw' and not self.connected:
            base_amount = (self.gross_amount * self.r_and_d_percentage) / 100
            restriction_amount = base_amount - self.eligible_amount
            return {
                'has_restriction': True,
                'restriction_type': '65% EPW cap',
                'original_amount': base_amount,
                'restriction_amount': restriction_amount,
                'final_amount': self.eligible_amount
            }
        return {
            'has_restriction': False,
            'restriction_type': None,
            'original_amount': self.eligible_amount,
            'restriction_amount': Decimal('0'),
            'final_amount': self.eligible_amount
        }


class GrantOrSubsidy(models.Model):
    """Grants or subsidies that affect claims"""
    
    APPLIES_TO_CHOICES = [
        ('claim', 'Entire Claim'),
        ('line_item', 'Specific Line Item'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='grants_subsidies')
    source = models.CharField(max_length=200, help_text="Source of grant/subsidy")
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    applies_to = models.CharField(max_length=20, choices=APPLIES_TO_CHOICES, default='claim')
    
    # Optional specific reference
    line_item = models.ForeignKey(CostLineItem, on_delete=models.CASCADE, blank=True, null=True)
    
    impact_description = models.TextField(help_text="Description of how this affects the claim")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['source', 'created_at']
        indexes = [
            models.Index(fields=['claim', 'applies_to']),
        ]
    
    def __str__(self):
        return f"{self.source} - £{self.amount} ({self.claim.name})"


class NarrativeSection(models.Model):
    """Narrative responses for claims"""

    # TODO: Add multiple projects 
    # TODO: Add project weightings for AIF
    
    QUESTION_CHOICES = [
        ('scientific_advance', 'What scientific advance was sought?'),
        ('technical_uncertainty', 'What technical uncertainty was overcome?'),
        ('r_and_d_activities', 'What R&D activities were undertaken?'),
        ('competent_professional', 'Competent professional analysis'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='narrative_sections')
    question = models.CharField(max_length=50, choices=QUESTION_CHOICES)
    custom_question = models.CharField(max_length=500, blank=True, help_text="Custom question if 'other' selected")
    response = models.TextField(help_text="Detailed response to the question")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['claim', 'question']
        ordering = ['question']
        indexes = [
            models.Index(fields=['claim', 'question']),
        ]
    
    def __str__(self):
        question_text = self.custom_question if self.question == 'other' else self.get_question_display()
        return f"{self.claim.name} - {question_text[:50]}..."


class Attachment(models.Model):
    """File attachments for claims"""
    
    ATTACHMENT_TYPES = [
        ('payroll', 'Payroll Data'),
        ('invoice', 'Invoice'),
        ('contract', 'Contract'),
        ('timesheet', 'Timesheet'),
        ('supporting_doc', 'Supporting Document'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, help_text="Original filename when uploaded")
    file_path = models.FileField(upload_to='claims/attachments/%Y/%m/')
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    file_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='other')
    description = models.TextField(blank=True, help_text="Description of the attachment")
    
    # User and timestamp information
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_attachments')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['claim', 'file_type']),
            models.Index(fields=['uploaded_by', 'uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} - {self.claim.name}"


class ReviewComment(models.Model):
    """Comments on claims or line items"""
    
    COMMENT_TYPES = [
        ('claim', 'Claim Comment'),
        ('line_item', 'Line Item Comment'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPES)
    
    # References to different objects
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='comments', blank=True, null=True)
    line_item = models.ForeignKey(CostLineItem, on_delete=models.CASCADE, related_name='comments', blank=True, null=True)
    
    # Comment content
    comment = models.TextField(help_text="Comment text")
    is_resolved = models.BooleanField(default=False, help_text="Whether this comment has been resolved")
    
    # User and timestamp information
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['comment_type', 'is_resolved']),
            models.Index(fields=['author', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.created_at.strftime('%Y-%m-%d')}"
    
    def get_related_object(self):
        """Get the object this comment relates to"""
        if self.line_item:
            return self.line_item
        else:
            return self.claim
