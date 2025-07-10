# Open-Source R&D Claim Platform: Planning Document

## Project Overview

Objective:
Build an open-source web application that helps users (R&D tax consultants) prepare UK R&D tax credit claims in a configurable, transparent, and auditable way.

Inspired by: 
Claimer.com — but open, advisor-friendly, and extensible.

## Next steps

## Goals

* Enable users to upload financial data (payroll, trial balance, etc.)
* Let users define column mappings and inclusion/exclusion logic
* Automatically calculate qualifying R&D expenditure
* Provide clear exportable outputs for CT600L and claim documentation
* Allow configuration of claim logic (e.g. via YAML or web UI)
* Be fully open source and self-hostable

## Features

### Must have

* 1 . Claim Calculation Logic
    + Support per-employee overrides (e.g. Alice = 100%, Bob = 50%)
    + Allow EPW “connected/unconnected” tagging
    + Cap EPW at 65% of eligible cost
    + Automatically apply NIC uplift and adjustable percentages
    + Add grant/subsidy tracking at cost line level
    + Flag potentially ineligible costs (e.g. high PILON, bonuses)

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
rd-machine/
├── app.py
├── templates/
│   ├── upload.html
│   ├── map_columns.html
│   └── results.html
├── static/
│   └── styles.css
├── rd_logic/
│   ├── processor.py
│   ├── mappings.py
│   └── reporter.py
├── uploads/
├── config/
│   └── settings.yaml
├── data/
│   └── sample_payroll.xlsx
├── README.md
├── requirements.txt
└── Dockerfile
```

## Flow

### User

* User uploads data file (Excel/CSV)
* System extracts column headers
* User maps fields (e.g., "Gross Salary" → Column B)
* User sets exclusions (e.g., exclude "PILON", "Mat")
* User sets default R&D % or per-person value
* System processes and shows results
* User downloads summary or CT600L-ready table