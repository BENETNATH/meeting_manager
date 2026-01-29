# Database Migration Commands

## Production Database Setup

**IMPORTANT**: The application no longer uses `db.create_all()` automatically. Use Flask-Migrate for proper database schema management.

### Initial Setup

1. **Initialize Migration Repository**:
   ```bash
   flask db init
   ```

2. **Create Initial Migration**:
   ```bash
   flask db migrate -m "Initial migration"
   ```

3. **Apply Migration**:
   ```bash
   flask db upgrade
   ```

### Ongoing Development

When you modify models:

1. **Create Migration**:
   ```bash
   flask db migrate -m "Description of changes"
   ```

2. **Apply Migration**:
   ```bash
   flask db upgrade
   ```

### Production Deployment

1. **Generate Migration on Development**:
   ```bash
   flask db migrate -m "Production changes"
   ```

2. **Deploy Migration Files** to production server

3. **Apply Migration in Production**:
   ```bash
   flask db upgrade
   ```

### Migration Commands Reference

- `flask db init` - Initialize migration repository
- `flask db migrate -m "message"` - Create new migration
- `flask db upgrade` - Apply migrations
- `flask db downgrade` - Rollback migrations
- `flask db history` - Show migration history
- `flask db current` - Show current migration
- `flask db heads` - Show head migrations

### Environment Variables Required

Before running migrations, ensure these environment variables are set:

```bash
export FLASK_APP=run.py
export FLASK_ENV=production  # or development
export SQLALCHEMY_DATABASE_URI="postgresql://user:password@localhost/dbname"
export SECRET_KEY="your-secret-key"
```

### Admin User Creation

After migrations, create the admin user manually:

```python
from app import create_app
from app.models import User, db

app = create_app('production')
with app.app_context():
    admin = User(username='admin', email='admin@example.com', role='super-admin')
    admin.set_password('your-admin-password')
    db.session.add(admin)
    db.session.commit()