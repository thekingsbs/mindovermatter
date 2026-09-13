# Mind Over Matter

Site for the Mind Over Matter psychology education organization: events,
resources, contact, and a quiz that records SONA credit claims.

## Running it locally

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env          # edit SECRET_KEY at minimum
    python manage.py migrate
    python manage.py seed_demo    # sample chapters, events, and a quiz
    python manage.py createsuperuser
    python manage.py runserver

The seed command also creates a staff account `gtofficer` / `changeme123`
scoped to the Georgia Tech chapter, so you can see what a chapter officer
sees. Delete it before you go live.

SQLite is the default. Set `DATABASE_URL` to switch to Postgres.

## How credit works

1. An officer creates an event in the admin, sets `credit_value`, writes an
   `attendance_code`, and attaches a quiz.
2. The code is read out in the last few minutes of the session.
3. Students take the quiz. The submission is stored with
   `credit_status = pending`.
4. An officer reviews submissions and runs **Mark selected as verified**.
5. **Export SONA roster** produces the CSV to hand to the participant pool
   coordinator, and flips those rows to `exported`.

Nothing writes to SONA directly. The roster CSV is the handover point, so
this works no matter what your department's process turns out to be.

## Apps

- `core` — chapters, officer profiles, resources, contact, privacy
- `events` — events and the attendance code
- `quizzes` — quizzes, questions, submissions, scoring, SONA export

## Things that are deliberate

**High school chapters never collect data.** `Chapter.save()` forces
`collects_submissions` and `sona_enabled` off for `kind = high_school`, and
the quiz form refuses submissions from a chapter that doesn't collect them.
Collecting names and answers from minors needs school sign-off and parental
consent that this project doesn't handle.

**Scoring is server-side only.** `quizzes/scoring.py` reads correctness from
the `Choice` table. Nothing in the request body affects the score.

**One submission per student per quiz.** Enforced by a database constraint on
`(quiz, lower(school_identifier))`, not just a form check, so a double-click
or a race can't slip a second one through.

**Chapter officers only see their own chapter.** `ChapterScopedAdmin` filters
every queryset by the logged-in user's `OfficerProfile.chapter`. Officers with
no chapter set, and superusers, see everything.

**Schools are a fixed list, never free text.** The school field resolves to a
Chapter row, so the database never accumulates "GT" / "Ga Tech" / "georgia
tech" as separate schools. Students whose school isn't listed land in
`SchoolRequest` instead.

## Before you launch

- Have someone at your school read `templates/pages/privacy.html`. It is a
  starting point, not legal advice.
- Talk to the participant pool coordinator at each university before turning
  `sona_enabled` on. Ask whether org talks are eligible for pool credit at
  all, what identifier they need, and what roster format they want.
- Set `DEBUG=0` and a real `SECRET_KEY`.
- Delete the seeded demo rows and the `gtofficer` account.

## Deploying

Render or Railway both work. Build with
`pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`,
start with `gunicorn config.wsgi`, and set the environment variables from
`.env.example`.
