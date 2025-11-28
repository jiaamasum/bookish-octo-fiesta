# Class Exam Management System (CEMS)

A Django 5.2 project for managing classes, exams, and results. The current snapshot focuses on secure authentication and static UI previews while the domain workflows are being rebuilt.

## Current Scope
- Authentication: login/logout, student self-sign-up, password reset (raises an error when an email is unknown), console email backend for local testing.
- Role routing: redirects authenticated users to role dashboards; catch-all URLs and 404s return to the home view.
- Profiles: `TeacherProfile` with auto-generated employee codes (`EMP###`), `StudentProfile` with generated IDs (`225002###`) that never get overwritten, and a safeguard that removes any student profile when a teacher profile is created.
- Dashboards: landing page plus Super Admin, Teacher, and Student dashboards rendered as static previews with placeholder stats and copy.
- Styling: shared base layout with Space Grotesk/Manrope fonts and static assets under `cems/static`.

## Recent Updates
- Rebuilt the landing page and all dashboards as static previews while class/exam/result flows are paused.
- Added a role-aware mixin to push logged-in users away from auth pages to their correct dashboard.
- Hardened password reset to surface errors when the email does not exist.
- Implemented automatic identifiers for teachers and students, including persistence guards and cleanup when a user becomes a teacher.
- Added a catch-all URL + 404 handler that redirect to the home view to keep navigation consistent.

## Tech Stack
- Python 3.x, Django 5.2.8
- PostgreSQL (default local settings: database `class_exam_db`, user `postgres`, password `masumjia`, host `127.0.0.1`, port `5432`)
- HTML templates with static CSS/JS in `cems/static`

## Getting Started
1. Create and activate a virtual environment: `python -m venv venv && venv\\Scripts\\activate` (or `source venv/bin/activate`).
2. Install dependencies: `pip install -r requirements.txt`.
3. Create the PostgreSQL database using the credentials above (or update `cems/settings.py`).
4. Run migrations: `python manage.py migrate`.
5. Create a superuser for Django admin: `python manage.py createsuperuser`.
6. Start the server: `python manage.py runserver` and open `http://127.0.0.1:8000/`.

## Key URLs
- Landing page: `/`
- Student sign-up: `/accounts/register/student/`
- Login / Logout: `/accounts/login/` and `/accounts/logout/`
- Password reset: `/accounts/password-reset/`
- Role redirect: `/accounts/role-redirect/`
- Dashboards (static previews): `/accounts/dashboard/student/`, `/accounts/dashboard/teacher/`, `/accounts/admin/`
- Django admin: `/admin/`

## Notes
- Dashboards are intentionally static; data-backed class, exam, and results workflows are temporarily disabled.
- Student IDs are generated when `assign_student_id()` is invoked (e.g., during future enrollment flows) and are preserved on subsequent saves.
