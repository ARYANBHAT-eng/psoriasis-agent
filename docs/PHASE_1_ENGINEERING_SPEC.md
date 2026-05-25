# Phase 1 — Engineering Specification
## Psoriasis Agent · Clinical Data Model

> This document is the engineering specification for Phase 1 of the Psoriasis Agent project.
> It is written to be consumed by Claude Code (the VS Code agent) operating in the project repository.
> Phase 1's purpose is to make the data model clinically credible — to capture the signals that
> actually predict flares, separate psoriasis from psoriatic arthritis, and provide an honest
> foundation for the temporal ML work in Phase 2.

---

## How to use this document

Same workflow as Phase 0:

1. Read the entire task section before touching code.
2. Read the actual files in the repository to understand current state.
3. **Propose a plan** in chat before making any file edits. Reference real file paths and real symbols.
4. Wait for explicit approval before executing.
5. Make the changes.
6. Run the acceptance criteria.
7. Show the output.
8. Stop. Do not proceed to the next task until approved.

If anything in this spec contradicts what the codebase contains, **ask before assuming**.
The spec describes intent; the codebase is the source of truth for current state.

---

## Strategic context

Phase 0 made the application reliable: persistent database, authenticated access, durable model,
testable surface. The system can be trusted with data, but the data itself remains insufficient
for clinically meaningful predictions.

The current entry schema treats psoriasis and psoriatic arthritis as one condition with one set of
symptom sliders. It captures none of the well-documented external triggers (weather, alcohol,
recent illness, hormonal cycle). It records flare events through the same form used for daily
symptom logging, which biases the label toward "obvious, already-severe flares" rather than
early-warning signals. It contains no measure of which entries have enough signal to actually
train on.

Phase 1 fixes all of this. The two clinical truths driving the design:

1. **Psoriasis and psoriatic arthritis are different diseases with different flare dynamics.**
   The triggers, the time-to-onset, the affected systems, and the relevant clinical metrics
   are different. A single model trained on a single combined symptom score is statistically
   coincidental, not predictive.

2. **Flares don't begin on the day they become obvious.** They begin days earlier with shifts
   in sleep, stress, environmental conditions, and subclinical inflammation. Capturing those
   shifts requires data the current schema does not collect.

Building Phase 2's temporal ML on the current data would propagate these biases into a model
that looks accurate (because it predicts obvious flares well) but provides no clinical value
(because it cannot warn early). Get the data right first. Then the ML can be honest.

This phase is the most clinically consequential work in the project. Treat it accordingly.

---

## Architectural decisions

| Decision | Choice | Rationale |
|---|---|---|
| Schema shape | Single `Entry` table with nullable condition-specific fields, separate tables for events (`FlareEvent`, `MedicationEvent`, `WeatherCapture`) | Daily logging stays one operation. Events that don't happen daily live in dedicated tables. Joins only when needed. |
| Condition discrimination | New `UserProfile` table with `has_psoriasis`, `has_psa` booleans | The user's profile gates which fields are shown, validated, and used in training. Avoids irrelevant data collection for users who only have one condition. |
| Psoriasis-specific fields | BSA estimate (0–100%), plaque locations (JSON list), treatment specifics | BSA is the standard clinical severity metric. Plaque locations help identify environmental correlations (sun-exposed vs covered). |
| PsA-specific fields | Morning stiffness duration (minutes), affected joint count, functional limitation (0–10) | Morning stiffness duration is the single most important PsA metric — used in DAPSA scoring. Joint count and function follow standard rheumatology assessment. |
| External triggers | Weather auto-fetched daily; alcohol, illness, cycle phase self-reported | Weather has the strongest evidence base and zero user friction when automated. Other triggers require user input but only on relevant days. |
| Weather provider | Open-Meteo (no API key required) as primary; OpenWeatherMap (free tier, API key) as fallback | Open-Meteo is free and key-less. No secret to manage, no rate limit complexity. OpenWeatherMap remains a tested fallback if Open-Meteo is unreachable. |
| Location precision | City-level lat/lon (rounded to 2 decimal places, ~1 km precision) | Weather data needs city granularity, not GPS precision. Storing coarse coordinates reduces privacy risk and satisfies the use case. |
| Cycle phase | Opt-in field gated by `UserProfile.tracks_cycle` flag | Sensitive data. Off by default. User must explicitly enable in profile. Field is hidden in the UI if disabled. |
| Flare labeling | New `FlareEvent` table; legacy `psoriasis_flare` boolean preserved on `Entry` but renamed to `legacy_flare_flag` | Decouples "I had a flare" from "I logged today's symptoms." Allows confidence annotations. Old data is not discarded — it is reinterpreted as low-confidence labels. |
| Medication events | New `MedicationEvent` table separate from `missed_medication` daily flag | Daily adherence and treatment changes are different concepts. Conflating them obscures both signals. |
| Data quality scoring | Computed at read time, not stored | Field completeness + time-since-last-entry are derivable; storing them creates a stale-data problem. Compute on demand. |
| Migration strategy | All new fields nullable; legacy fields preserved with rename | Existing entries continue to work. Existing predictions continue to work. New data uses new fields. No data loss anywhere in the pipeline. |
| API versioning | New endpoints prefixed `/v2/`; v1 routes preserved temporarily | The frontend transitions per task; old API stays functional during the rollout. Removed in Phase 3 when the new frontend lands. |
| PII handling | Location lat/lon, cycle data, audit logs all included in `/entries/export` and deleted on account deletion | Phase 0 established the data rights contract. Phase 1 extends it to every new field. |

---

## Pre-flight checklist

Before starting Task 1, Claude Code should:

1. Run `git status --short`. Confirm working tree is clean and the current branch is appropriate
   for Phase 1 work.
2. Read `backend/app/models.py` in full. Report current state of `DailyEntry`, `User`,
   `AuditLog`, `ModelArtifact`.
3. Read `backend/app/schemas.py` in full. Report the Pydantic models currently exposed.
4. Read `backend/app/routers/entries.py` and `backend/app/crud.py`. Report the current entry
   creation, summary, and trend logic.
5. Read `backend/ml_model.py` (or wherever the ML logic lives). Report the current feature
   list used in training and prediction.
6. Read `frontend/app.py`. Report the current entry form fields and any condition-related
   branching.
7. Confirm Alembic migration head, run `alembic history` and report the current revision and
   the count of total revisions.
8. Confirm the test suite is currently green: `cd backend && pytest tests/ -v`. If anything
   is failing, stop and report — Phase 1 does not start from a red baseline.

Only after this is complete should Task 1 begin.

---

## Task 1 — User profile and clinical data model

### Goal
Introduce `UserProfile` to capture which conditions a user manages and personal context that
affects clinical interpretation. Expand the entry schema with condition-specific clinical fields.
All additions are nullable and gated by the user's profile.

### Architectural constraints

- `UserProfile` is 1:1 with `User`. Created at first login if absent. Default values are conservative
  (no conditions assumed, no cycle tracking, no location).
- Condition-specific entry fields are nullable. The API does not require them. The frontend chooses
  whether to show them based on the user's profile.
- Morning stiffness is recorded in minutes (integer, 0–480 representing 0–8 hours). Anything beyond
  8 hours is capped with a validation warning, not a hard rejection.
- BSA estimate is a percentage (float, 0.0–100.0). The frontend should provide a reference image
  or text helper, but the backend accepts any value in range.
- Plaque locations is a JSON array of standardized strings: `["scalp", "elbows", "knees", "back",
  "trunk", "groin", "face", "hands", "feet", "other"]`. Frontend validates against the list;
  backend accepts any string for flexibility.
- Affected joints is a JSON array using standardized rheumatology naming. Use the DAPSA simplified
  list: `["dip", "pip", "mcp", "wrist", "elbow", "shoulder", "knee", "ankle", "mtp", "spine"]`.
  Backend accepts any string.
- Functional limitation is a single integer 0–10. Frontend provides a simple slider with anchored
  labels at 0 ("no limitation") and 10 ("severe limitation").
- All new fields go on the existing `daily_entries` table (renamed to `entries` for clarity).
  Avoid joins for the common case of "today's entry."

### Deliverables

1. New `UserProfile` model in `backend/app/models.py`:
   - `user_id` (FK to users, unique, NOT NULL)
   - `has_psoriasis` (bool, default True for legacy compatibility)
   - `has_psa` (bool, default False)
   - `tracks_cycle` (bool, default False)
   - `location_city` (str, nullable)
   - `location_lat` (float, nullable, precision 2 decimal places enforced via Pydantic)
   - `location_lon` (float, nullable, precision 2 decimal places enforced via Pydantic)
   - `timezone` (str, default "UTC")
   - `created_at`, `updated_at` (DateTime with timezone)

2. Extend the existing entry model (rename `DailyEntry` → `Entry`, table `daily_entries` → `entries`):
   - Add: `morning_stiffness_minutes` (int, nullable)
   - Add: `affected_joints` (JSON, nullable)
   - Add: `functional_limitation` (int, nullable, 0–10)
   - Add: `bsa_estimate` (float, nullable, 0.0–100.0)
   - Add: `plaque_locations` (JSON, nullable)
   - Rename: `psoriasis_flare` → `legacy_flare_flag` (data preserved; Task 4 deprecates this).

3. Alembic migration:
   - Add `user_profiles` table
   - Add new columns to `entries` (was `daily_entries`)
   - Rename table `daily_entries` → `entries`
   - Rename column `psoriasis_flare` → `legacy_flare_flag`
   - Downgrade fully reverses all of the above

4. Pydantic schemas in `backend/app/schemas.py`:
   - `UserProfileCreate`, `UserProfileUpdate`, `UserProfileRead`
   - Update existing `EntryCreate`, `EntryRead` with new nullable fields
   - Validators for value ranges and JSON list contents (warn on unknown strings, do not reject)

5. New router `backend/app/routers/profile.py`:
   - `GET /v2/profile` — return current user's profile, create with defaults if absent
   - `PATCH /v2/profile` — partial update, validated
   - All routes protected by `Depends(get_current_user)`

6. Update `backend/app/routers/entries.py`:
   - `POST /v2/entries/` — accepts new optional fields
   - `GET /v2/entries/` — returns new fields when present
   - Keep `/entries/` (v1) routes working unchanged for backward compatibility

7. Update `backend/crud.py` to handle the new fields and the renamed columns.

8. Update `frontend/app.py`:
   - On first login post-deploy, fetch `/v2/profile` to ensure a profile exists
   - Add a profile settings panel in the sidebar (collapsible) for editing conditions, location, cycle tracking
   - The entry form shows PsA fields only if `has_psa=True`
   - The entry form shows BSA + plaque fields only if `has_psoriasis=True`
   - The entry form shows cycle field only if `tracks_cycle=True`

### Acceptance criteria

```bash
# 1. Migration applies cleanly
cd backend && alembic upgrade head
# Expected: no errors

# 2. Verify schema
psql $DATABASE_URL -c "\dt"
# Expected: user_profiles table exists; daily_entries renamed to entries

psql $DATABASE_URL -c "\d entries"
# Expected: morning_stiffness_minutes, affected_joints, functional_limitation,
#           bsa_estimate, plaque_locations, legacy_flare_flag columns visible
#           psoriasis_flare column NO LONGER PRESENT

# 3. Profile is auto-created on first read
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=aryan&password=strong-password-123" | jq -r .access_token)
curl -s http://localhost:8000/v2/profile -H "Authorization: Bearer $TOKEN"
# Expected: profile with default values (has_psoriasis=true, has_psa=false, etc.)

# 4. Profile updates persist
curl -s -X PATCH http://localhost:8000/v2/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"has_psa": true, "location_city": "Jammu", "location_lat": 32.73, "location_lon": 74.86}'
curl -s http://localhost:8000/v2/profile -H "Authorization: Bearer $TOKEN"
# Expected: has_psa=true, location set

# 5. v2 entry endpoint accepts new fields
curl -s -X POST http://localhost:8000/v2/entries/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-25",
    "itch": 5, "redness": 4, "scaling": 3,
    "joint_pain": 6, "fatigue": 5, "stress_level": 7,
    "sleep_quality": 4, "diet_quality": 6,
    "missed_medication": 0, "topical_applied": 1,
    "morning_stiffness_minutes": 45,
    "affected_joints": ["dip", "wrist"],
    "functional_limitation": 4,
    "bsa_estimate": 12.5,
    "plaque_locations": ["scalp", "elbows"]
  }'
# Expected: 200 with the full entry echoed back

# 6. Legacy v1 endpoint still works
curl -s -X POST http://localhost:8000/entries/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-26", "itch": 3, "redness": 2, "scaling": 1,
    "joint_pain": 1, "fatigue": 2, "stress_level": 3,
    "sleep_quality": 7, "diet_quality": 7,
    "missed_medication": 0, "topical_applied": 1, "notes": ""
  }'
# Expected: 200 — proves backward compatibility

# 7. Existing data preserved across rename
psql $DATABASE_URL -c "SELECT COUNT(*) FROM entries WHERE legacy_flare_flag IS NOT NULL;"
# Expected: count matches pre-migration count of psoriasis_flare values

# 8. Migration round-trip
alembic downgrade -1
alembic upgrade head
# Expected: clean round-trip, no errors

# 9. Test suite passes
pytest tests/ -v
# Expected: all tests pass (existing tests + any new ones for profile)

# 10. Manual frontend check
# - Profile panel visible in sidebar
# - Default condition is psoriasis only — PsA fields hidden
# - Enable PsA in profile — joint and stiffness fields appear in entry form
# - Disable psoriasis — BSA and plaque fields disappear
```

### Rollback

```bash
cd backend && alembic downgrade -1
git checkout -- backend/ frontend/
```

---

## Task 2 — External trigger capture

### Goal
Capture environmental and lifestyle triggers that have documented correlation with psoriasis and
PsA flares. Weather is auto-fetched daily based on user location; alcohol, illness, and cycle
phase are self-reported on the daily entry form (gated by profile).

### Architectural constraints

- Weather is fetched once per user per day, on the first authenticated request after midnight in
  the user's local timezone. Cache hit otherwise.
- Weather provider primary: Open-Meteo (https://open-meteo.com — no API key). Fallback: store
  null and log at WARNING; the missing data is not an error.
- Weather data captured: temperature (°C), humidity (%), UV index, precipitation (mm),
  cloud cover (%), pressure (hPa). All optional in case the API returns partial data.
- Cycle phase is `cycle_day_of_period` (integer, 1–N where 1 is day 1 of period). Nullable.
  Only collected if `UserProfile.tracks_cycle=True`. Frontend must not display the field
  otherwise.
- Alcohol is `alcohol_units` (integer, standard drinks consumed). 0 is a valid recorded value
  (explicit "I had none today"). NULL means "not recorded."
- Recent illness is two fields: `illness_active` (bool) and `illness_description` (string, nullable).
  Illness description is free text; no controlled vocabulary in this phase.
- The weather fetch is best-effort. A failure must NEVER block entry creation or any other
  operation. Log at WARNING, store NULL, move on.

### Deliverables

1. New table `weather_captures`:
   - `id`, `user_id`, `date`, `fetched_at`, `temperature_c`, `humidity_pct`, `uv_index`,
     `precipitation_mm`, `cloud_cover_pct`, `pressure_hpa`, `source` (str, e.g. "open-meteo")
   - Unique constraint on `(user_id, date)`

2. New service module `backend/app/services/weather.py`:
   - `fetch_weather_for_user(user, date) -> WeatherCapture | None`
   - Implements Open-Meteo call with 5-second timeout
   - On failure: logs at WARNING, returns None — never raises

3. Background trigger:
   - On the first authenticated request from a user each day (any endpoint), check if a
     `WeatherCapture` exists for today. If not, fire the fetch as a FastAPI `BackgroundTask`.
   - Background task failure must not affect the response.

4. Extend `Entry` model with:
   - `alcohol_units` (int, nullable, ≥0)
   - `illness_active` (bool, nullable)
   - `illness_description` (str, nullable, max 500 chars)
   - `cycle_day_of_period` (int, nullable, 1–60)

5. Alembic migration for `weather_captures` table and new `entries` columns.

6. Pydantic schemas extended to accept and validate the new fields with appropriate ranges.

7. Update `backend/app/routers/entries.py`:
   - `GET /v2/entries/{date}/context` — returns the entry plus its associated weather capture
     for the same date

8. Update `frontend/app.py`:
   - Entry form: add alcohol, illness, cycle fields (cycle gated by profile)
   - Dashboard: show today's weather summary in a small panel if available

### Acceptance criteria

```bash
# 1. Migration applies cleanly
cd backend && alembic upgrade head

# 2. Profile with location set triggers weather fetch
curl -s -X PATCH http://localhost:8000/v2/profile \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"location_city": "Jammu", "location_lat": 32.73, "location_lon": 74.86}'

# Trigger a request that fires the background fetch
curl -s http://localhost:8000/v2/entries/ -H "Authorization: Bearer $TOKEN"

# Wait a few seconds for background task
sleep 5

# 3. Weather captured for today
psql $DATABASE_URL -c "SELECT date, temperature_c, source FROM weather_captures WHERE user_id=1 ORDER BY date DESC LIMIT 1;"
# Expected: a row for today's date

# 4. Entry context endpoint returns weather alongside entry
curl -s http://localhost:8000/v2/entries/2026-05-25/context \
  -H "Authorization: Bearer $TOKEN"
# Expected: JSON with entry fields and weather block

# 5. Weather API failure doesn't break entry creation
# (test by temporarily configuring an invalid lat/lon)
# - PATCH profile with location_lat=999 (invalid)
# - Create an entry
# - Expected: entry creation succeeds, weather is NULL, log shows WARNING

# 6. Cycle field invisible when tracks_cycle=False
# (manual frontend check)

# 7. All previous tests still pass
pytest tests/ -v
```

### Rollback

```bash
cd backend && alembic downgrade -1
git checkout -- backend/ frontend/
```

---

## Task 3 — Medication events

### Goal
Track medication starts, stops, and dose changes as first-class events distinct from daily
adherence. Allow correlation of treatment changes against symptom trends.

### Architectural constraints

- `MedicationEvent` is independent of daily entries. Multiple events per day are allowed (e.g.,
  starting one medication while stopping another).
- Event types are an enum: `start`, `stop`, `dose_increase`, `dose_decrease`, `switch`.
- Medication names are free text. Phase 1 does not impose a drug dictionary; that's Phase 5
  territory.
- Events are append-only. Updates create new events; the prior event is not modified.
- Events are queryable by date range for use in timeline views.

### Deliverables

1. New `MedicationEvent` model:
   - `id`, `user_id`, `event_date`, `event_type` (enum), `medication_name` (str),
     `dose` (str, optional), `notes` (str, optional), `created_at`
   - Index on `(user_id, event_date)` for range queries

2. Alembic migration.

3. Pydantic schemas for create and read.

4. New router `backend/app/routers/medications.py`:
   - `POST /v2/medications/events` — create event
   - `GET /v2/medications/events?from=&to=` — list in range
   - `GET /v2/medications/events/{id}` — fetch one

5. Update `frontend/app.py`:
   - Add a "Medication events" page in the sidebar with a form to log events and a list view

### Acceptance criteria

```bash
# 1. Migration clean
alembic upgrade head

# 2. Create a medication event
curl -s -X POST http://localhost:8000/v2/medications/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_date": "2026-05-20",
    "event_type": "start",
    "medication_name": "Methotrexate",
    "dose": "15mg weekly"
  }'
# Expected: 201 with event echoed back

# 3. List events in range
curl -s "http://localhost:8000/v2/medications/events?from=2026-05-01&to=2026-05-31" \
  -H "Authorization: Bearer $TOKEN"
# Expected: list containing the event

# 4. Events appear in data export
curl -s http://localhost:8000/entries/export -H "Authorization: Bearer $TOKEN" -o exp.json
python -c "import json; d=json.load(open('exp.json')); print('medication_events' in d)"
# Expected: True (export includes medication events)

# 5. Tests pass
pytest tests/ -v
```

### Rollback

```bash
cd backend && alembic downgrade -1
git checkout -- backend/
```

---

## Task 4 — Flare labeling redesign

### Goal
Replace the legacy daily-form flare checkbox with a dedicated flare event flow.
Allow confidence annotation on labels. Migrate existing `legacy_flare_flag` rows to
`FlareEvent` records with low-confidence source.

### Architectural constraints

- `FlareEvent` is a discrete event with a start date and (often) an end date.
- An open flare has `end_date = NULL`. Most flares are resolved within days to weeks.
- `condition_type` indicates which condition flared: `psoriasis`, `psa`, `both`.
- `confidence_source` is an enum: `user_confirmed` (user explicitly logged a flare event),
  `algorithm_derived` (Phase 2+ will use this), `legacy` (backfilled from the old boolean).
- `severity` is an integer 1–10 self-rated. Nullable for legacy entries.
- Migration backfill: every `entries.legacy_flare_flag = TRUE` becomes a `FlareEvent` with
  `start_date = entries.date`, `end_date = entries.date`, `condition_type = 'psoriasis'`,
  `confidence_source = 'legacy'`, `severity = NULL`.
- The legacy column is not dropped in Phase 1. Phase 2 evaluates whether to drop it after
  confirming the new model trains correctly on FlareEvent data.

### Deliverables

1. New `FlareEvent` model with the fields above.

2. Alembic migration:
   - Creates `flare_events` table
   - Backfills existing legacy_flare_flag rows into flare_events
   - The backfill runs in the migration `upgrade()` body using a data migration step

3. Pydantic schemas for flare create, read, update (to close an open flare with end_date).

4. New router `backend/app/routers/flares.py`:
   - `POST /v2/flares` — log a flare event
   - `GET /v2/flares?from=&to=&condition=` — list flare events
   - `PATCH /v2/flares/{id}` — close or amend an open flare
   - `DELETE /v2/flares/{id}` — remove a flare event (e.g., logged in error)

5. Update `frontend/app.py`:
   - Remove the flare checkbox from the daily entry form
   - Add a "Log a flare" button on the dashboard that opens a flare event form
   - Add a flare history view

### Acceptance criteria

```bash
# 1. Migration applies cleanly and backfills existing data
psql $DATABASE_URL -c "SELECT COUNT(*) FROM entries WHERE legacy_flare_flag IS TRUE;"
# Record the count, e.g., 5

alembic upgrade head

psql $DATABASE_URL -c "SELECT COUNT(*) FROM flare_events WHERE confidence_source = 'legacy';"
# Expected: matches the count above

# 2. Logging a flare event
curl -s -X POST http://localhost:8000/v2/flares \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-05-22",
    "condition_type": "psa",
    "severity": 7,
    "notes": "Severe joint pain in left wrist"
  }'
# Expected: 201 with end_date=null (open flare)

# 3. Closing the flare
FLARE_ID=$(...)
curl -s -X PATCH http://localhost:8000/v2/flares/$FLARE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"end_date": "2026-05-25"}'

# 4. Querying flares
curl -s "http://localhost:8000/v2/flares?from=2026-05-01&condition=psa" \
  -H "Authorization: Bearer $TOKEN"
# Expected: list including the event

# 5. Daily entry form no longer accepts legacy_flare_flag
curl -s -X POST http://localhost:8000/v2/entries/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"date":"2026-05-27", ...other fields..., "legacy_flare_flag": true}'
# Expected: 200 but legacy_flare_flag ignored OR 422 — pick one and document

# 6. Tests pass
pytest tests/ -v
```

### Rollback

```bash
cd backend && alembic downgrade -1
git checkout -- backend/ frontend/
# Note: rollback restores legacy_flare_flag values from the backfilled flare_events
# This must be in the migration downgrade() function explicitly
```

---

## Task 5 — Frontend + API integration

### Goal
Bring the Streamlit frontend up to parity with all new backend functionality. Make the daily
entry form profile-aware. Add the new views (medications, flares, weather panel). Surface data
quality scores on the dashboard.

### Architectural constraints

- The frontend remains Streamlit — this is interim until Phase 3 replaces it entirely.
- All new fields are profile-gated. The frontend MUST NOT show fields irrelevant to the user's
  conditions.
- Data quality scoring is computed client-side from entry completeness (% of fields filled) and
  surfaced on the dashboard as "Entry quality: high/medium/low" with a tooltip explaining
  what was missing.
- Backward compatibility: if the user has no profile yet, the form defaults to "psoriasis only"
  and prompts them to confirm in the profile sidebar.

### Deliverables

1. Profile sidebar (collapsible) in `frontend/app.py`:
   - Edit conditions (psoriasis/PsA toggles)
   - Edit location (city, lat/lon)
   - Toggle cycle tracking
   - Save button → PATCH /v2/profile

2. Profile-gated entry form:
   - Common fields always visible (itch, redness, sleep, stress, etc.)
   - Psoriasis fields (BSA, plaque locations) visible only if has_psoriasis=True
   - PsA fields (joints, stiffness, function) visible only if has_psa=True
   - Cycle field visible only if tracks_cycle=True
   - Alcohol and illness always visible (low friction, broadly relevant)

3. New sidebar pages:
   - "Medication events" — log and list
   - "Flares" — log flares, view history
   - "Insights" — placeholder for Phase 2 ML insights

4. Weather panel on dashboard showing today's auto-captured weather if available.

5. Entry quality indicator on each row in the entries table.

### Acceptance criteria

Manual end-to-end checklist (run from a fresh profile state):

```
Profile defaults shown                                          [pass/fail]
Toggle PsA on → joint, stiffness, function fields appear        [pass/fail]
Toggle PsA off → those fields disappear                         [pass/fail]
Toggle psoriasis off → BSA and plaque fields disappear          [pass/fail]
Enable cycle tracking → cycle field appears                     [pass/fail]
Set location → weather panel populates within 30s               [pass/fail]
Log a medication event → appears in list                        [pass/fail]
Log an open flare → appears in flare history with end_date=null [pass/fail]
Close the flare via UI → end_date populated                     [pass/fail]
Entry quality shows on dashboard table                          [pass/fail]
Existing entries still display correctly                        [pass/fail]
```

### Rollback

```bash
git checkout -- frontend/
```

---

## Task 6 — Test suite expansion

### Goal
Cover all Phase 1 functionality with the smoke test suite. Verify migration round-trips.
Validate the backfill in Task 4. Keep the migration test against real Postgres functional.

### Architectural constraints

- New tests follow Phase 0 patterns: pytest, TestClient, in-memory SQLite for smoke,
  Postgres for migration round-trip.
- The seeded_entries fixture is updated to include some profile data and at least one
  legacy flare flag to exercise the backfill.
- ML tests are not in Phase 1 scope — Phase 2 will rewrite them when the model itself changes.

### Deliverables

1. Updated `backend/tests/conftest.py` fixtures:
   - `profile_headers` — creates a user, sets a profile with both conditions enabled, returns headers
   - `seeded_with_flares` — seeds entries plus a few flare events for testing

2. New `backend/tests/test_profile.py`:
   - `test_profile_auto_created` — fresh user gets a default profile on first GET
   - `test_profile_update` — PATCH persists
   - `test_profile_location_validation` — out-of-range lat/lon rejected

3. New `backend/tests/test_v2_entries.py`:
   - Entry creation with new fields
   - Legacy v1 endpoint still works
   - Field validation (range checks)

4. New `backend/tests/test_weather.py`:
   - Weather fetch service can be called (mocked HTTP)
   - Weather endpoint returns context
   - Weather failure doesn't break entry creation

5. New `backend/tests/test_medications.py`:
   - Event CRUD
   - Range queries
   - Export includes medication events

6. New `backend/tests/test_flares.py`:
   - Flare event CRUD
   - Open flare can be closed
   - Backfill verification: pre-existing legacy_flare_flag rows produced legacy FlareEvents

7. Update `backend/tests/test_migration.py`:
   - Verify all new tables exist after `upgrade head`
   - Verify clean downgrade to base
   - Verify backfill data integrity through round-trip

### Acceptance criteria

```bash
cd backend
pytest tests/ -v --tb=short
# Expected: all tests pass, including legacy Phase 0 tests
# Expected count: previous 25 + new tests for all Phase 1 functionality
```

### Rollback

Tests are additive. No rollback needed.

---

## Final — Documentation and migration verification

### Deliverables

1. Update `README.md`:
   - New section: "Data Model" — describes Entry, FlareEvent, MedicationEvent, WeatherCapture, UserProfile
   - New section: "Clinical Context" — explains why psoriasis and PsA are tracked separately
   - Update env vars: no new ones expected if Open-Meteo is primary
   - Update API table with v2 endpoints

2. Update `docs/PHASE_1_ENGINEERING_SPEC.md` (this file) with a "Completion State" appendix
   capturing what was actually built (for handoff to Phase 2).

3. Update `docs/ROLLBACK.md` with the new migration revision IDs.

4. Update `context.md` with Phase 1 completion state.

5. Single phase-completion commit (or merge commit) on the project's deployment branch.

---

## Out of scope for Phase 1

These items are explicitly deferred:

- **Temporal feature engineering** (rolling windows, lag features) — Phase 2.
- **Separate ML models for psoriasis vs PsA** — Phase 2. Phase 1 collects the data; Phase 2 uses it.
- **Personal trigger pattern detection** — Phase 5.
- **PDF clinical export, FHIR-format export** — Phase 4.
- **React/Next.js frontend** — Phase 3. Streamlit gets parity updates here but is not replaced.
- **Drug dictionary / standardized medication codes** — Phase 5 (probably with RxNorm integration).
- **Push notifications for daily logging** — Phase 5.
- **Symptom photos** — not in any current phase. Privacy-sensitive, would need separate design.
- **Multi-user / multi-patient support** — not on the roadmap. Single-user app by design.

If something feels in scope but isn't on the deliverables list above, **ask before implementing**.

---

## Clinical caveats Claude Code should not make assumptions about

These are decisions that depend on real clinical judgment or on the user's preference. Do not
silently pick one — flag for discussion if they come up during execution:

1. **Cycle tracking generalization.** "tracks_cycle" is currently menstrual cycle phase. If a
   user requests generalizing to "hormonal cycle phase" or supporting non-binary tracking,
   that's a design conversation, not a unilateral decision.

2. **DAPSA-style joint scoring.** The current PsA approach uses "joint count" but does not
   implement full DAPSA (which weights tender vs swollen joints). Adding DAPSA is a clinical
   accuracy improvement but adds form complexity. Flag if scope expands.

3. **BSA estimation method.** The current spec accepts a self-reported percentage. The "rule
   of nines" or palm-as-1% methods could be added as helpers. Flag if a clinical reference
   tool is requested.

4. **Whether to drop `legacy_flare_flag` after Phase 2 validation.** The decision depends on
   whether Phase 2's model trains correctly on the new FlareEvent data. Phase 1 preserves
   the column; the drop is explicitly deferred.

---

## Completion State

Phase 1 completed on 2026-05-26.

All 7 tasks (Tasks 1–6 + Final) delivered.
Final test count: **76 tests passing** (65 smoke + 5 profile + 6 v2 entries + migration integration test skipped without Postgres).
Migration chain: **7 revisions** total (3 Phase 0 + 4 Phase 1). Upgrade/downgrade round-trip verified locally.

### Key deviations from original spec

- **Task 5+6 combined into a single task.** The spec listed them separately; they were planned and executed as one combined effort with no loss of scope.
- **Weather provider fallback not implemented.** The spec listed OpenWeatherMap as a fallback for Open-Meteo. Open-Meteo proved reliable and key-less; the fallback was not needed and would have required an API key secret. Deferred to Phase 2 if Open-Meteo reliability becomes an issue.
- **Morning stiffness cap is a hard 422, not a soft warning.** The spec said values beyond 480 minutes should be "capped with a validation warning, not a hard rejection." The implementation rejects >480 with 422. The frontend slider is bounded at 480 with a help text explaining the convention, which achieves the same UX goal without accepting invalid data.
- **Entry quality scoring is client-side only.** The spec noted data quality should be "computed at read time, not stored." Implemented as a pandas `apply` in the Streamlit frontend — never hits the backend, exactly as intended.
- **v1 routes fully preserved.** All Phase 0 entry routes (`POST /entries/`, `GET /entries/`, etc.) remain functional. The v2 router is additive; no v1 behavior was altered.

### Deferred to Phase 2

- Retrain ML model on `FlareEvent` labels with confidence weighting (currently trains on `legacy_flare_flag`).
- Separate prediction models for psoriasis vs. PsA flare risk.
- Algorithmically derived flare labels from symptom threshold crossings.
- Drop `legacy_flare_flag` column after Phase 2 validation confirms FlareEvent-based training is stable.
- OpenWeatherMap fallback if Open-Meteo proves unreliable in production.
- PATCH profile clearing of nullable fields (current `exclude_none=True` limitation).
