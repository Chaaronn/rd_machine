# Open-Source R&D Claim Platform: Planning Document

## Project Overview

Objective:
Build an open-source web application that helps users (R&D tax consultants) prepare UK R&D tax credit claims in a configurable, transparent, and auditable way.

Inspired by: 
Claimer.com — but open, advisor-friendly, and extensible.

## Next steps

## Goals

* Enable users to upload financial data (payroll, trial balance, etc.)
      + Completed
* Let users define column mappings and inclusion/exclusion logic
      + Completed
* Automatically calculate qualifying R&D expenditure
* Provide clear exportable outputs for CT600L and claim documentation
* Allow configuration of claim logic (e.g. via YAML or web UI)
* Be fully open source and self-hostable

## Features

### Must have

* 1 . Claim Calculation Logic
    + Support per-employee overrides (e.g. Alice = 100%, Bob = 50%)
    + Allow EPW/Subcon “connected/unconnected” tagging
        - Cap at 65% of eligible cost
    + Automatically apply NIC cap and adjustable percentages
    + Add grant/subsidy tracking at cost line level and final level
    + Flag potentially ineligible costs (e.g. PILON, bonuses, recharges)

* 2. Data Mapping & Import 
    + Pre-save mapping templates for common formats (Xero, Sage, etc.)
    + Support merging multiple input sheets (payroll + timesheets + TB)
    + Regex or keyword-based auto-mapping suggestions
        - Driven from the consultant side
    + File version control — track changes across re-uploads

* 3. User Roles & Collaboration
    + Role-based permissions: Consultant vs Reviewer
    + Add review/approval step before export
    + Commenting or annotation on cost lines (“exclude – interco recharge”)

* 4. Export & Reporting Enhancements
    + Generate CT600L-ready summary sheet
    + Produce audit trail (why something was excluded, who did it)
    + Generate narrative scaffolding from structured inputs
        - i.e., questions from the templates (what is advance in relation to baseline etc.)
    + Include project timeline breakdown

* 5. UI/UX 
    + R&D calculator preview with real-time updates
    + “Explain this” tooltips for every config/decision
    + Save draft claims and return later
    + Upload supporting evidence (PDFs, emails, patent docs)

### In future

* Automated flagging of areas for review
    + i.e., "detected recharge in balance_sheet.xlsx in sheet A on line X"
    + possibly using regex or fuzzy. 
        - both should allow consultant/reviewer to set specifics
* Link to specific sections of CTA/DSIT/CIRD for reasoning
    + i.e., on Unconnected EPW restriction, show CTA S1131 & CIRD84000 

## Structure

```
rd_machine/
├── manage.py
├── requirements.txt
├── README.md
├── rd_claimer/                    # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   ├── asgi.py
│   └── wsgi.py
├── claims/                        # Main claims app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   ├── logic/                     # R&D calculation logic
│   │   ├── processor.py
│   │   ├── reporter.py
│   │   └── rules.yaml
│   ├── management/                # Django management commands
│   │   └── commands/
│   │       └── populate_sample_data.py
│   ├── migrations/
│   ├── static/claims/
│   │   └── styles.css
│   └── templates/claims/
│       ├── claim_create.html
│       ├── claim_detail.html
│       ├── claim_list.html
│       ├── claim_update.html
│       ├── claim_delete.html
│       ├── cost_category_detail.html
│       ├── mapping_create.html
│       ├── mapping_list.html
│       ├── mapping.html
│       ├── narrative.html
│       ├── results.html
│       └── upload.html
├── users/                         # User management app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   ├── migrations/
│   └── templates/users/
│       ├── login.html
│       ├── register.html
│       ├── profile.html
│       └── edit_profile.html
├── templates/                     # Base templates
│   ├── base.html
│   └── home.html
├── config/                        # Configuration files
│   └── example_mapping.yaml
├── scripts/                       # Utility scripts
│   └── import_claim_data.py
└── docs/                         # Documentation
    ├── planning.md
    └── changelog.md
```

## R&D Rules

### Overall

* Client level tagging
    + SME / RDEC 
        - This would affect the calculations for any claim created
    + Specific mappings

### Staff 

No specific rules needed here, its more to do with the tagging of columns
to ensure the correct items are included/excluded. 

Needs to be a method for estimating PAYE cap for SME claims

### Subcontractors 

Needs to be a method of tagging un/connected

When unconnected, restrict to 65% 
When connected, prompt for user input for the lesser of comparison 
* Lesser of; amount paid to subcontractor vs amount spent by subcon

This is similar for EPWs. 



## Flow

### Creating new client 


* User add cli


### Claim

* User uploads data file (Excel/CSV)
* System extracts column headers
* User maps fields (e.g., "Gross Salary" → Column B)
* User sets exclusions (e.g., exclude "PILON", "Mat")
* User sets default R&D % or per-person value
* System processes and shows results
* User downloads summary or CT600L-ready table


# Prelim Screenshots

## Claim management 

### Overview 

<img width="1380" height="923" alt="image" src="https://github.com/user-attachments/assets/8168d2d0-9554-4256-b91c-7c799d8b11ad" />

### Claim view 

<img width="1335" height="901" alt="image" src="https://github.com/user-attachments/assets/31386eea-36e8-4c9b-b95a-19228cac3c51" />

### Data upload 

<img width="1405" height="930" alt="image" src="https://github.com/user-attachments/assets/e3cb0cb3-2b3e-4400-91c9-36de9f74b4b7" />

### Post-Upload

<img width="1424" height="865" alt="image" src="https://github.com/user-attachments/assets/e541f417-8595-4de4-aa97-b946f4c81ddc" />

### Detailed view of cost category

<img width="1434" height="928" alt="image" src="https://github.com/user-attachments/assets/23c51d25-745f-467f-8514-55b3b8115d53" />

### Editing a specific line-item

<img width="923" height="876" alt="image" src="https://github.com/user-attachments/assets/0de31627-bfe6-4fe9-b06a-7a35c95eab56" />

