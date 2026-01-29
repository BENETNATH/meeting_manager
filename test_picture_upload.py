#!/usr/bin/env python3
"""
Test script for picture upload functionality.
This script tests the picture upload feature to ensure it works correctly.
"""

import os
import sys
import tempfile
from PIL import Image

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Event, User
from app.services.event_service import EventService

def create_test_image(filename, width=1000, height=600):
    """Create a test image file."""
    img = Image.new('RGB', (width, height), color='red')
    img.save(filename)
    return filename

def test_picture_upload():
    """Test the picture upload functionality."""
    print("Testing picture upload functionality...")
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        # Create a test user
        test_user = User(
            username='test_user',
            email='test@example.com',
            role='editor'
        )
        test_user.set_password('test_password')
        
        try:
            db.session.add(test_user)
            db.session.commit()
            print("✓ Test user created")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Failed to create test user: {e}")
            return False
        
        # Create a test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image_path = create_test_image(temp_file.name)
        
        try:
            # Test picture upload
            from werkzeug.datastructures import FileStorage
            
            with open(test_image_path, 'rb') as f:
                file_storage = FileStorage(
                    stream=f,
                    filename='test_picture.jpg',
                    content_type='image/jpeg'
                )
                
                # Test the _save_picture method
                filename = EventService._save_picture(file_storage)
                
                if filename:
                    print(f"✓ Picture uploaded successfully: {filename}")
                    
                    # Check if file exists
                    upload_path = os.path.join('uploads', filename)
                    if os.path.exists(upload_path):
                        print("✓ Picture file exists in uploads directory")
                        
                        # Check file size
                        file_size = os.path.getsize(upload_path)
                        print(f"✓ Picture file size: {file_size} bytes")
                        
                        # Clean up
                        os.remove(upload_path)
                        print("✓ Test picture file cleaned up")
                    else:
                        print("✗ Picture file not found in uploads directory")
                        return False
                else:
                    print("✗ Picture upload failed")
                    return False
                    
        except Exception as e:
            print(f"✗ Error during picture upload test: {e}")
            return False
        finally:
            # Clean up test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
            
            # Clean up test user
            try:
                db.session.delete(test_user)
                db.session.commit()
                print("✓ Test user cleaned up")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Failed to clean up test user: {e}")
        
        print("\n✓ All picture upload tests passed!")
        return True

def test_event_creation_with_picture():
    """Test creating an event with a picture upload."""
    print("\nTesting event creation with picture upload...")
    
    app = create_app()
    with app.app_context():
        # Create a test user
        test_user = User(
            username='test_user2',
            email='test2@example.com',
            role='editor'
        )
        test_user.set_password('test_password')
        
        try:
            db.session.add(test_user)
            db.session.commit()
            print("✓ Test user created")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Failed to create test user: {e}")
            return False
        
        # Create a test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            test_image_path = create_test_image(temp_file.name)
        
        try:
            # Test event creation with picture
            from werkzeug.datastructures import FileStorage
            
            with open(test_image_path, 'rb') as f:
                file_storage = FileStorage(
                    stream=f,
                    filename='test_event_picture.jpg',
                    content_type='image/jpeg'
                )
                
                # Prepare event data
                event_data = {
                    'title': 'Test Event with Picture',
                    'description': 'This is a test event with an uploaded picture.',
                    'program': 'Test program content.',
                    'date': '2026-02-01',
                    'start_time': '10:00',
                    'end_time': '16:00',
                    'organizer': 'Test Organizer',
                    'location': 'Test Location',
                    'eligible_hours': 6.0,
                    'status': 'visible',
                    'timezone': 'UTC',
                    'picture': file_storage,
                    'signature': None
                }
                
                # Create event
                success, message = EventService.create_event_service(event_data, test_user.id)
                
                if success:
                    print("✓ Event created successfully with picture upload")
                    
                    # Find the created event
                    event = Event.query.filter_by(title='Test Event with Picture').first()
                    if event and event.photo_filename:
                        print(f"✓ Event has photo_filename: {event.photo_filename}")
                        
                        # Check if picture file exists
                        upload_path = os.path.join('uploads', event.photo_filename)
                        if os.path.exists(upload_path):
                            print("✓ Event picture file exists in uploads directory")
                            
                            # Clean up
                            os.remove(upload_path)
                            print("✓ Event picture file cleaned up")
                        else:
                            print("✗ Event picture file not found in uploads directory")
                            return False
                    else:
                        print("✗ Event not found or no photo_filename")
                        return False
                else:
                    print(f"✗ Event creation failed: {message}")
                    return False
                    
        except Exception as e:
            print(f"✗ Error during event creation test: {e}")
            return False
        finally:
            # Clean up test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)
            
            # Clean up test event and user
            try:
                event = Event.query.filter_by(title='Test Event with Picture').first()
                if event:
                    db.session.delete(event)
                    db.session.commit()
                    print("✓ Test event cleaned up")
                
                db.session.delete(test_user)
                db.session.commit()
                print("✓ Test user cleaned up")
            except Exception as e:
                db.session.rollback()
                print(f"✗ Failed to clean up test data: {e}")
        
        print("\n✓ Event creation with picture upload test passed!")
        return True

if __name__ == '__main__':
    print("Picture Upload Functionality Test")
    print("=" * 40)
    
    # Ensure uploads directory exists
    os.makedirs('uploads', exist_ok=True)
    
    # Run tests
    test1_passed = test_picture_upload()
    test2_passed = test_event_creation_with_picture()
    
    print("\n" + "=" * 40)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! Picture upload functionality is working correctly.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Please check the implementation.")
        sys.exit(1)