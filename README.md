# TrendLine

TrendLine is a Django news web app with authentication, a user dashboard, profile management, and news/chat APIs powered by NewsAPI.

## Features

- User registration, login, logout
- Protected dashboard for signed-in users
- News endpoints for trending, recent, category-based, and sidebar feeds
- Chat-style news assistant endpoint
- User profile page and profile update/avatar upload APIs
- Login session and user activity tracking
- Customized Django admin for users, profiles, sessions, and activity

## Tech Stack

- Python 3
- Django 5
- SQLite
- HTML/CSS/JavaScript templates
- NewsAPI integration

## Project Structure

```text
TrendLine/
  README.md
  myproject/
    manage.py
    myproject/
      settings.py
      urls.py
      .env
    trendline/
      models.py
      views.py
      urls.py
      forms.py
    templates/
```

## Local Setup

1. Go to the Django project directory:

```powershell
cd myproject
```

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install django requests python-dotenv pillow
```

4. (Optional) Set environment variables in `myproject/.env`:

```env
GOOGLE_API_KEY=your_key_here
```

5. Apply migrations:

```powershell
python manage.py migrate
```

6. Run the development server (defaults to port `8002`):

```powershell
python manage.py runserver
```

## Default URLs

- App home: `http://127.0.0.1:8002/`
- Admin: `http://127.0.0.1:8002/admin/`
- Register: `http://127.0.0.1:8002/register/`
- Login: `http://127.0.0.1:8002/login/`
- Dashboard: `http://127.0.0.1:8002/dashboard/`

## API Endpoints

- `GET /get-news/<category>/`
- `GET /get-news/?topic=<topic>`
- `GET /api/trending/`
- `GET /api/trending/advanced/`
- `GET /api/recent/`
- `GET /api/sidebar/`
- `GET /api/profile/`
- `POST /api/profile/update/`
- `POST /api/profile/avatar/`
- `POST /api/chat/`
- `GET /api/test/`

## Notes

- `CSRF_TRUSTED_ORIGINS` is configured for localhost on port `8002`.
- The project currently contains hardcoded NewsAPI usage in `trendline/views.py`; move API keys to environment variables before production use.
