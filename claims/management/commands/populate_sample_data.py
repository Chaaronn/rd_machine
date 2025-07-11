from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime, date

from claims.models import (
    Claim, CostCategory, CostLineItem, GrantOrSubsidy, 
    NarrativeSection, Attachment, ReviewComment
)


class Command(BaseCommand):
    help = 'Populate the database with sample claims data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username to create claims for (default: admin)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing claims data before populating'
        )

    def handle(self, *args, **options):
        username = options['username']
        clear_data = options['clear']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create the user if it doesn't exist
            user = User.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password='admin123'
            )
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created user "{username}" with password "admin123"')
            )
        
        if clear_data:
            # Clear existing data
            Claim.objects.filter(created_by=user).delete()
            self.stdout.write(
                self.style.WARNING('Cleared existing claims data.')
            )
        
        # Create sample claims
        self.create_sample_claims(user)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated sample claims data!')
        )

    def create_sample_claims(self, user):
        """Create sample claims with realistic data"""
        
        # Claim 1: ABC Ltd - In Progress
        claim1 = Claim.objects.create(
            name='ABC Ltd R&D Claim 2023-24',
            company='ABC Ltd',
            accounting_period_start=date(2023, 4, 1),
            accounting_period_end=date(2024, 3, 31),
            description='Software development and AI research projects focusing on machine learning algorithms and data processing systems.',
            status='in_review',
            created_by=user,
            total_costs=Decimal('125000.00'),
            eligible_costs=Decimal('87500.00'),
            credit_amount=Decimal('22750.00')
        )
        
        # Create cost categories for claim 1
        staff_category1 = CostCategory.objects.create(
            claim=claim1,
            category='staff',
            total_cost=Decimal('75000.00'),
            eligible_cost=Decimal('60000.00'),
            description='Development team salaries and benefits'
        )
        
        software_category1 = CostCategory.objects.create(
            claim=claim1,
            category='software',
            total_cost=Decimal('25000.00'),
            eligible_cost=Decimal('20000.00'),
            description='Development tools and cloud services'
        )
        
        consumables_category1 = CostCategory.objects.create(
            claim=claim1,
            category='consumables',
            total_cost=Decimal('25000.00'),
            eligible_cost=Decimal('7500.00'),
            description='Hardware and testing materials'
        )
        
        # Create line items for claim 1
        CostLineItem.objects.create(
            claim=claim1,
            type='staff',
            name='John Smith',
            role='Senior Software Engineer',
            r_and_d_activity='Leading AI algorithms development and machine learning model training',
            gross_amount=Decimal('45000.00'),
            r_and_d_percentage=Decimal('80.00'),
            cost_date=date(2023, 6, 15),
            notes='Lead developer on AI algorithms',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim1,
            type='staff',
            name='Sarah Johnson',
            role='Data Scientist',
            r_and_d_activity='Full-time machine learning research and model optimisation',
            gross_amount=Decimal('30000.00'),
            r_and_d_percentage=Decimal('100.00'),
            cost_date=date(2023, 7, 1),
            notes='Full-time on machine learning research',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim1,
            type='software',
            name='AWS Cloud Services',
            company_name='Amazon Web Services',
            role='Cloud Computing',
            r_and_d_activity='Machine learning model training and data processing infrastructure',
            gross_amount=Decimal('15000.00'),
            r_and_d_percentage=Decimal('90.00'),
            cost_date=date(2023, 8, 1),
            notes='GPU instances for model training',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim1,
            type='software',
            name='TensorFlow Enterprise',
            company_name='Google',
            role='ML Framework',
            r_and_d_activity='Deep learning model development and training',
            gross_amount=Decimal('10000.00'),
            r_and_d_percentage=Decimal('100.00'),
            cost_date=date(2023, 9, 1),
            notes='Enterprise ML framework licence',
            uploaded_by=user
        )
        
        # Create narrative sections for claim 1
        NarrativeSection.objects.create(
            claim=claim1,
            question='scientific_advance',
            response='The project aimed to advance the field of machine learning by developing novel algorithms for real-time data processing with improved accuracy and reduced computational requirements.'
        )
        
        NarrativeSection.objects.create(
            claim=claim1,
            question='technical_uncertainty',
            response='The main technical uncertainties involved optimising algorithm performance while maintaining accuracy, and developing scalable solutions for large datasets that existing techniques could not handle efficiently.'
        )
        
        # Claim 2: XYZ Corp - Completed
        claim2 = Claim.objects.create(
            name='XYZ Corp R&D Claim 2023-24',
            company='XYZ Corp',
            accounting_period_start=date(2023, 4, 1),
            accounting_period_end=date(2024, 3, 31),
            description='Medical device development and testing for innovative cardiac monitoring systems.',
            status='completed',
            created_by=user,
            total_costs=Decimal('250000.00'),
            eligible_costs=Decimal('175000.00'),
            credit_amount=Decimal('45500.00')
        )
        
        # Create cost categories for claim 2
        staff_category2 = CostCategory.objects.create(
            claim=claim2,
            category='staff',
            total_cost=Decimal('150000.00'),
            eligible_cost=Decimal('120000.00'),
            description='Research and development team'
        )
        
        equipment_category2 = CostCategory.objects.create(
            claim=claim2,
            category='other',
            total_cost=Decimal('75000.00'),
            eligible_cost=Decimal('37500.00'),
            description='Medical testing equipment and devices'
        )
        
        subcontractor_category2 = CostCategory.objects.create(
            claim=claim2,
            category='subcontractor',
            total_cost=Decimal('25000.00'),
            eligible_cost=Decimal('17500.00'),
            description='Specialist medical consulting services'
        )
        
        # Create line items for claim 2
        CostLineItem.objects.create(
            claim=claim2,
            type='staff',
            name='Dr. Emma Wilson',
            role='Chief Medical Officer',
            r_and_d_activity='Leading medical device research and clinical trial design',
            gross_amount=Decimal('80000.00'),
            r_and_d_percentage=Decimal('75.00'),
            cost_date=date(2023, 5, 1),
            notes='Leading medical device research',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim2,
            type='staff',
            name='Michael Chen',
            role='Biomedical Engineer',
            r_and_d_activity='Device design, prototyping, and testing protocols',
            gross_amount=Decimal('50000.00'),
            r_and_d_percentage=Decimal('90.00'),
            cost_date=date(2023, 6, 1),
            notes='Device design and testing',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim2,
            type='staff',
            name='Lisa Brown',
            role='Research Technician',
            r_and_d_activity='Laboratory testing, data collection, and analysis',
            gross_amount=Decimal('20000.00'),
            r_and_d_percentage=Decimal('100.00'),
            cost_date=date(2023, 7, 1),
            notes='Laboratory testing and data collection',
            uploaded_by=user
        )
        
        # Add subcontractor
        CostLineItem.objects.create(
            claim=claim2,
            type='subcontractor',
            name='MedTech Consultants Ltd',
            company_name='MedTech Consultants Ltd',
            role='Regulatory Consulting',
            r_and_d_activity='FDA approval process guidance and regulatory compliance',
            gross_amount=Decimal('25000.00'),
            r_and_d_percentage=Decimal('70.00'),
            connected=True,  # Connected subcontractor
            cost_date=date(2023, 8, 15),
            notes='FDA approval process guidance',
            uploaded_by=user
        )
        
        # Claim 3: Tech Solutions - Draft with EPW examples
        claim3 = Claim.objects.create(
            name='Tech Solutions R&D Claim 2023-24',
            company='Tech Solutions Ltd',
            accounting_period_start=date(2023, 4, 1),
            accounting_period_end=date(2024, 3, 31),
            description='Renewable energy research and development of advanced solar panel technology.',
            status='draft',
            created_by=user,
            total_costs=Decimal('75000.00'),
            eligible_costs=Decimal('52000.00'),
            credit_amount=Decimal('13520.00')
        )
        
        # Create cost categories for claim 3
        staff_category3 = CostCategory.objects.create(
            claim=claim3,
            category='staff',
            total_cost=Decimal('35000.00'),
            eligible_cost=Decimal('28000.00'),
            description='Internal research team'
        )
        
        epw_category3 = CostCategory.objects.create(
            claim=claim3,
            category='epw',
            total_cost=Decimal('30000.00'),
            eligible_cost=Decimal('14000.00'),  # After EPW restrictions
            description='External specialists'
        )
        
        consumables_category3 = CostCategory.objects.create(
            claim=claim3,
            category='consumables',
            total_cost=Decimal('10000.00'),
            eligible_cost=Decimal('10000.00'),
            description='Testing materials and components'
        )
        
        # Create line items for claim 3
        CostLineItem.objects.create(
            claim=claim3,
            type='staff',
            name='David Lee',
            role='Senior Research Engineer',
            r_and_d_activity='Solar panel efficiency research and photovoltaic cell development',
            gross_amount=Decimal('35000.00'),
            r_and_d_percentage=Decimal('80.00'),
            cost_date=date(2023, 6, 1),
            notes='Leading solar technology research',
            uploaded_by=user
        )
        
        # Connected EPW (no restriction)
        CostLineItem.objects.create(
            claim=claim3,
            type='epw',
            name='GreenTech Specialists',
            company_name='GreenTech Specialists Ltd',
            role='Connected EPW',
            r_and_d_activity='Renewable energy system optimisation and advanced materials research',
            gross_amount=Decimal('15000.00'),
            r_and_d_percentage=Decimal('100.00'),
            connected=True,  # Connected EPW - no cap
            cost_date=date(2023, 7, 1),
            notes='Connected EPW - no cap applied',
            uploaded_by=user
        )
        
        # Unconnected EPW (65% restriction applies)
        CostLineItem.objects.create(
            claim=claim3,
            type='epw',
            name='Solar Innovations Ltd',
            company_name='Solar Innovations Ltd',
            role='Unconnected EPW',
            r_and_d_activity='Advanced photovoltaic research and testing protocols',
            gross_amount=Decimal('15000.00'),
            r_and_d_percentage=Decimal('80.00'),
            connected=False,  # Unconnected EPW - 65% cap applies
            cost_date=date(2023, 8, 1),
            notes='Unconnected EPW - 65% cap applied',
            uploaded_by=user
        )
        
        CostLineItem.objects.create(
            claim=claim3,
            type='consumables',
            name='Testing Materials',
            role='Research Supplies',
            r_and_d_activity='Solar panel testing and analysis materials',
            gross_amount=Decimal('10000.00'),
            r_and_d_percentage=Decimal('100.00'),
            cost_date=date(2023, 9, 1),
            notes='Silicon wafers, testing equipment, chemicals',
            uploaded_by=user
        )
        
        # Create narrative sections for claim 3
        NarrativeSection.objects.create(
            claim=claim3,
            question='scientific_advance',
            response='The project sought to advance solar panel technology by developing new photovoltaic cell designs with improved efficiency and reduced manufacturing costs.'
        )
        
        NarrativeSection.objects.create(
            claim=claim3,
            question='technical_uncertainty',
            response='Key technical uncertainties included optimising cell efficiency while maintaining durability, and developing cost-effective manufacturing processes for novel materials.'
        )
        
        # Create a sample grant for claim 3
        GrantOrSubsidy.objects.create(
            claim=claim3,
            source='Innovate UK',
            amount=Decimal('5000.00'),
            applies_to='claim',
            impact_description='Partial funding for renewable energy research project'
        )
        
        self.stdout.write(
            self.style.SUCCESS('Created sample claims:')
        )
        self.stdout.write(f'  - {claim1.name} (Status: {claim1.status})')
        self.stdout.write(f'  - {claim2.name} (Status: {claim2.status})')
        self.stdout.write(f'  - {claim3.name} (Status: {claim3.status})')
        
        # Print summary
        total_claims = Claim.objects.filter(created_by=user).count()
        total_line_items = CostLineItem.objects.filter(claim__created_by=user).count()
        
        self.stdout.write(
            self.style.SUCCESS(f'Summary: {total_claims} claims, {total_line_items} line items')
        ) 