# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Initial Project Setup

### Added
- **Django Project Structure**: Created rd_machine project with rd_claimer as the main Django application
- **Claims Application**: Comprehensive claims management system with:
  - Models for claim data storage
  - Full CRUD operations (Create, Read, Update, Delete)
  - Template system for claim management interfaces
  - Administrative interface integration
  - Custom forms for claim data entry
  
- **User Management System**: Complete user authentication and profile management
  - User registration and login functionality
  - Profile management with edit capabilities
  - Custom user templates

- **Claims Processing Logic**: 
  - Processor module for claim data processing
  - Reporter module for generating claim reports
  - Rules engine with YAML configuration support

- **Data Management**:
  - Management command for populating sample data
  - Import script for claim data migration
  - Database migrations for both claims and users applications

- **Template System**:
  - Base template for consistent site layout
  - Home page template
  - Comprehensive claim management templates:
    - Claim listing and detail views
    - Claim creation and update forms
    - Claim deletion confirmation
    - Cost category details
    - Mapping management interface
    - Narrative and results display
    - File upload functionality

- **Configuration**:
  - Example mapping configuration in YAML format
  - Django settings configuration
  - URL routing for both claims and users applications

- **Static Assets**:
  - CSS styling for claims interface
  - Media upload handling
  - Static file serving configuration

- **Documentation**:
  - Planning documentation
  - Project requirements specification
  - Initial project structure documentation

### Project Structure
```
rd_machine/
├── claims/          # Claims management application
├── users/           # User authentication and profiles
├── rd_claimer/      # Main Django project configuration
├── templates/       # Global templates
├── static/          # Static assets
├── media/           # User uploads
├── docs/            # Documentation
├── config/          # Configuration files
└── scripts/         # Utility scripts
```

### Technical Stack
- **Framework**: Django (Python web framework)
- **Database**: SQLite (default Django configuration)
- **Template Engine**: Django Templates
- **Configuration**: YAML for mapping rules
- **Static Files**: CSS for styling

### Notes
This represents the initial project setup with core functionality for claims processing and user management. The system is designed to handle R&D tax relief claim management with a focus on data processing, reporting, and user workflow management. 