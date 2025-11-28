# Class Exam Management System (CEMS)

A Django 5.2 project for running school academics and exam workflows end-to-end with role-aware dashboards for students, teachers, and admins.

## Features
- Auth and roles: login/logout, student self-sign-up, password reset that errors on unknown emails, role-based redirect, and a catch-all route that returns users to the correct dashboard.
- Profiles and identity: teacher profiles auto-generate employee codes (`EMP###`); student profiles generate permanent IDs (`225002###`), keep roll numbers in sync with enrollments, and drop any existing student profile when a teacher profile is created for the same user.
- Academic structure: migrations seed AcademicYears 2024-2050, ClassLevels CLASS 6-CLASS 10, Subjects BANGLA/ENGLISH/MATH/SCIENCE, and every year/class ClassOffering combination.
- Enrollments: one active enrollment per student per academic year; roll numbers auto-increment within a class offering; student IDs are assigned on first enrollment and never overwritten.
- Teacher assignments: one teacher per class-offering/subject, blocked for past academic years; helpers in `academics.services` simplify assignment creation.
- Exams and marks: admins or assigned teachers can create exams for the current year only, with no past dates and subject totals capped at 100 marks; marks entry is limited to the class roster and disabled while an exam is in draft; per-student averages and letter grades are computed across subjects.
- Promotions: admin-only promotion batches advance students when every subject average is at least 40%; otherwise they repeat. Existing target enrollments are skipped, and PromotionResult rows record passed/failed/skipped outcomes.
- Dashboards: student dashboard shows enrollment, roll, subjects, upcoming exams, marks, and historical performance with computed grades; teacher dashboard lists assignments, rosters, current/past exams, and mark entry; admin dashboard plus performance and promotion screens. All domain models are also registered in Django admin with a bulk "Promote selected classes" action.

## Project Layout
- `accounts/`: authentication views, role routing, dashboards, student registration, password reset form, and user profiles.
- `academics/`: domain models and services for years, classes, subjects, enrollments, teacher assignments, exams/marks, and promotions, plus admin customizations.
- `templates/`: HTML for landing/auth pages, dashboards, exam creation/marking, admin dashboards, and promotion admin override.
- `cems/static/`: shared CSS/JS assets referenced by the templates.
- `manage.py`, `cems/settings.py`, `cems/urls.py`: project setup and routing (including catch-all to the home/role redirect flow).

## Data Seeding
- Migrations seed AcademicYears 2024-2050, class levels CLASS 6-CLASS 10, subjects BANGLA, ENGLISH, MATH, SCIENCE, and all year/class ClassOfferings.
- Student IDs, teacher employee codes, and enrollment roll numbers are generated automatically as profiles and enrollments are created.

## Getting Started
1. Create and activate a virtual environment: `python -m venv venv && venv\\Scripts\\activate` (or `source venv/bin/activate`).
2. Install dependencies: `pip install -r requirements.txt`.
3. Create the PostgreSQL database (default: name `class_exam_db`, user `postgres`, password `masumjia`, host `127.0.0.1`, port `5432`) or update `cems/settings.py`.
4. Run migrations (seeds academic data): `python manage.py migrate`.
5. Create a superuser for Django admin: `python manage.py createsuperuser`.
6. Start the server: `python manage.py runserver` and open `http://127.0.0.1:8000/`.

## Typical Workflow
- Log into `/admin/` as a superuser to manage reference data or run promotions.
- Add teacher profiles and assign them to class offerings + subjects for the current academic year.
- Enroll students into class offerings (via Django admin or shell); IDs and rolls fill automatically.
- Teachers create exams from `/accounts/dashboard/teacher/exams/create/` and enter marks for their roster at `/accounts/dashboard/teacher/exams/<id>/` after publishing.
- Admins can review student performance at `/admin/performance/` and run promotions at `/admin/promote/` or via the ClassOffering admin action.

## Key URLs
- Landing page: `/`
- Student sign-up: `/accounts/register/student/`
- Login / Logout: `/accounts/login/` and `/accounts/logout/`
- Password reset: `/accounts/password-reset/`
- Role redirect: `/accounts/role-redirect/`
- Dashboards: `/accounts/dashboard/student/`, `/accounts/dashboard/teacher/`, `/accounts/admin/`
- Django admin: `/admin/`

## Notes
- Console email backend is enabled for password reset in development.
- Exam creation is limited to the current academic year; promotions cannot target future years.
