# LabHub Server

A Django-based queue management system for SpikeSortingLabHub.

## Project Structure

```
.
├── labhub/              # Django project configuration
│   ├── settings.py      # Project settings
│   ├── urls.py          # URL routing
│   ├── asgi.py          # ASGI application
│   └── wsgi.py          # WSGI application
├── Queue/               # Django Queue app
│   ├── models.py        # Queue model
│   ├── views.py         # ViewSet
│   ├── serializers.py   # DRF Serializers
│   ├── urls.py          # App URLs
│   ├── admin.py         # Admin configuration
│   └── migrations/      # Database migrations
├── manage.py            # Django management script
└── requirements.txt     # Project dependencies
```

## Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

- **Queue List/Create**: `GET/POST /api/queue/`
- **Queue Detail**: `GET/PUT/DELETE /api/queue/{id}/`
- **Admin**: `http://localhost:8000/admin`

## Features

- Queue management with status tracking
- REST API with Django REST Framework
- Django admin interface
- CORS support for frontend integration
- SQLite database

## Requirements

- Django 4.2.7
- djangorestframework 3.14.0
- django-cors-headers 4.3.1
- python-dotenv 1.0.0
