#!/usr/bin/env python3
"""Test script to check Flask template paths."""

import os
import sys
sys.path.insert(0, '.')

# Set minimal environment variables
os.environ['SECRET_KEY'] = 'test-key'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['MAIL_SERVER'] = 'localhost'
os.environ['MAIL_USERNAME'] = 'test@example.com'
os.environ['MAIL_PASSWORD'] = 'test'
os.environ['MAIL_DEFAULT_SENDER'] = 'test@example.com'

try:
    from app import create_app
    app = create_app()
    
    print("Flask app created successfully!")
    print(f"Template folder: {app.template_folder}")
    print(f"Jinja loader type: {type(app.jinja_env.loader)}")
    print(f"Jinja loader attributes: {dir(app.jinja_env.loader)}")
    
    # Try to get search paths differently
    if hasattr(app.jinja_env.loader, 'searchpath'):
        print("Template search paths:")
        for path in app.jinja_env.loader.searchpath:
            print(f"  - {path}")
    elif hasattr(app.jinja_env.loader, 'package_path'):
        print(f"Package path: {app.jinja_env.loader.package_path}")
    else:
        print("  - No searchpath or package_path attribute found")
        
    # Test if index.html can be found
    try:
        template = app.jinja_env.get_template('index.html')
        print(f"✓ index.html found at: {template.filename}")
    except Exception as e:
        print(f"✗ index.html not found: {e}")
        
    # Check current working directory
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if templates directory exists
    templates_dir = os.path.join(os.getcwd(), 'templates')
    print(f"Templates directory exists: {os.path.exists(templates_dir)}")
    
    if os.path.exists(templates_dir):
        print(f"Files in templates directory:")
        for file in os.listdir(templates_dir):
            print(f"  - {file}")
        
except Exception as e:
    print(f"Error creating app: {e}")
    import traceback
    traceback.print_exc()