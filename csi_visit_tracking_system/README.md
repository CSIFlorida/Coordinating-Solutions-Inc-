# CSI Visit Tracking System

A mobile-friendly web app (works great in a phone browser, no app store
needed) built from the CSI Visit Tracking System UI/UX outline. This
**replaces** the earlier WSC-based Visit Tracker.

## What this is (and isn't)

- **Is:** a responsive web app. Open it in a phone's browser (Chrome
  works best for voice dictation), and it behaves like an app — splash
  screen, bottom navigation, large tap targets, celebratory pop-ups.
- **Isn't:** a native iOS/Android app you'd submit to an app store. That
  would need a different toolchain (React Native/Flutter), app store
  developer accounts, and can't be built or published from inside this
  session. This gets you the same day-to-day experience without any of
  that overhead.

## Quick start

```bash
cd csi_visit_tracking_system
pip install -r requirements.txt
python3 import_consumers.py "/path/to/EMedi Stats ... WORKING DOC.xlsx"
python3 app.py
# open http://localhost:5000 — on a phone, use this computer's IP address
# instead of "localhost" so the phone can reach it over your network
```

On Windows, just double-click `run_csi_app.bat` — it installs everything,
imports the spreadsheet on first run, and opens your browser.

The very first person to open the app should tap **"Set Up Manager
Account"** on the splash screen. Everyone else signs up as a worker by
picking their worker code (the old WSC codes) from a list.

## Roles

**Manager** — top navigation: Dashboard, Data Upload, Reports, Workers.
Can re-upload the spreadsheet, view/export monthly reports by area, and
see completion stats per worker.

**Worker** — bottom navigation: Home, Visits, Profile. Sees only their
own assigned consumers, dictates or types visit notes, submits updates,
and gets a celebratory pop-up on completion.

## Area classification

Consumers are grouped into an Area based on city, per the spec:

- **Southers Area** — Miami-Dade County + Florida Keys
- **Southeast Area** — Broward County + Palm Beach County
- **Central Area** — Orlando + Central Florida

The mapping lives in `areas.py`. All 588 imported consumers matched a
known city — if a future upload includes a city not in that list, it'll
show as "Unclassified" so it's easy to spot and add.

## Voice dictation

Uses the browser's built-in Web Speech API — no external service, no
cost. Works well in Chrome and Edge (desktop and Android); Safari/iOS
support varies by version. If the API isn't available, the mic button
hides automatically and workers can just type the note instead.

## Authentication — what's real vs. what's deferred

- **Real and working:** phone number + password login. Passwords are
  hashed (never stored in plain text). Workers self-register by picking
  their worker code.
- **Deferred:** SMS two-factor authentication from the original spec.
  Sending real SMS codes requires a paid provider (e.g. Twilio) tied to
  your own account — I can't wire that up without your credentials.
  When you're ready, `auth.py` has a note on exactly where that step
  would plug into `login()` in `app.py`.

## Known data issue to review

Your spreadsheet has one duplicate iConnect Id (**68166**), listed twice
under slightly different names ("Barrios Jorge" assigned to worker CR,
and "Jorge Barrios" assigned to worker JGC) with different effective
dates but the same address/phone. The import keeps whichever row comes
last in the file (currently the JGC / "Jorge Barrios" version). Worth
checking with whoever maintains the source data — one of these WSC
assignments is probably a stale duplicate.

## Not yet built (flagged, not silently skipped)

- Native app packaging (see "What this is" above)
- Real SMS 2FA (needs your Twilio-style account)
- Animated screen transitions and haptic feedback (browser-based apps
  have real limits here compared to native)
- A manager-driven "invite a worker" flow — right now workers self-select
  an unclaimed worker code

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask app — all routes for both roles |
| `db.py` | SQLite schema + connection helper |
| `due_dates.py` | Visit-cadence math (unchanged from the WSC version) |
| `areas.py` | City → Area classification |
| `auth.py` | Password hashing, session helpers, role decorators |
| `import_consumers.py` | Loads the spreadsheet, classifies areas, seeds worker directory |
| `templates/`, `static/` | HTML/CSS/JS for both the worker and manager experiences |
| `run_csi_app.bat` | One-click Windows setup/launch |
