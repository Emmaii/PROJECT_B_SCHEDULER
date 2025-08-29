"""mvp_scheduler.py

MVP Scheduling script:
- Reads 'intake_responses.csv' with columns: name,email,preferred_slots
  preferred_slots: semicolon-separated datetimes in 'YYYY-MM-DD HH:MM' format (24-hour)
- Reads 'existing_bookings.csv' (optional) with columns: start_iso,end_iso
- For each intake row, finds the first preferred slot that does not overlap existing bookings
- Writes an .ics invite per confirmed booking into the 'out' folder
- Appends new bookings to existing_bookings.csv so repeated runs avoid duplicates
"""
from pathlib import Path
from datetime import datetime, timedelta
import csv
import sys
import uuid

DATA_DIR = Path(__file__).parent
INTAKE_CSV = DATA_DIR / 'intake_responses.csv'
EXISTING_CSV = DATA_DIR / 'existing_bookings.csv'
OUT_DIR = DATA_DIR / 'out'
OUT_DIR.mkdir(exist_ok=True)

DURATION_MINUTES = 30
TIMEZONE = 'Africa/Lagos'  # human-readable timezone for .ics timestamps

def read_existing_bookings():
    bookings = []
    if not EXISTING_CSV.exists():
        return bookings
    with EXISTING_CSV.open(newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            start = datetime.fromisoformat(r['start'])
            end = datetime.fromisoformat(r['end'])
            bookings.append((start, end))
    return bookings

def append_booking_to_existing(start, end):
    exists = EXISTING_CSV.exists()
    with EXISTING_CSV.open('a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(['start','end'])
        writer.writerow([start.isoformat(), end.isoformat()])

def slot_overlaps(start, end, bookings):
    for bstart, bend in bookings:
        # overlap if start < bend and end > bstart
        if start < bend and end > bstart:
            return True
    return False

def create_ics(summary, start_dt, duration_minutes, organizer_email, attendee_email, out_path):
    dtstart = start_dt.strftime('%Y%m%dT%H%M%S')
    dtend = (start_dt + timedelta(minutes=duration_minutes)).strftime('%Y%m%dT%H%M%S')
    uid = f"{uuid.uuid4()}@projectb.local"
    dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    ics_text = f"""BEGIN:VCALENDAR
PRODID:-//Project B Scheduling VA//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART;TZID={TIMEZONE}:{dtstart}
DTEND;TZID={TIMEZONE}:{dtend}
SUMMARY:{summary}
DESCRIPTION:Auto-generated appointment. If you need to reschedule, reply to the organizer email.
ORGANIZER;CN=Clinic:MAILTO:{organizer_email}
ATTENDEE;CN=Patient;RSVP=TRUE:MAILTO:{attendee_email}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""
    Path(out_path).write_text(ics_text, encoding='utf-8')

def main():
    if not INTAKE_CSV.exists():
        print('Create intake_responses.csv next to this script. See sample file provided.')
        sys.exit(1)
    bookings = read_existing_bookings()
    scheduled = []
    with INTAKE_CSV.open(newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['name'].strip()
            email = row['email'].strip()
            raw_prefs = row.get('preferred_slots','').strip()
            if not raw_prefs:
                print('No preferred slots for', name)
                continue
            prefs = [p.strip() for p in raw_prefs.split(';') if p.strip()]
            booked = False
            for p in prefs:
                try:
                    start_dt = datetime.fromisoformat(p)
                except Exception:
                    print('Invalid datetime format for', p, 'expected YYYY-MM-DD HH:MM, skipping.')
                    continue
                end_dt = start_dt + timedelta(minutes=DURATION_MINUTES)
                if not slot_overlaps(start_dt, end_dt, bookings):
                    summary = f'Initial Telehealth Consultation — {name}'
                    filename = OUT_DIR / f'invite_{name.replace(" ","_")}_{start_dt.strftime("%Y%m%dT%H%M")}.ics'
                    create_ics(summary, start_dt, DURATION_MINUTES, 'reception@clinic.example', email, filename)
                    append_booking_to_existing(start_dt, end_dt)
                    bookings.append((start_dt, end_dt))
                    scheduled.append((name, email, start_dt.strftime('%Y-%m-%d %H:%M'), str(filename)))
                    print('Scheduled', name, 'at', start_dt.isoformat(), '->', filename)
                    booked = True
                    break
            if not booked:
                print('Could not find a free preferred slot for', name)
    print('\nSummary:')
    print(f'Successfully scheduled {len(scheduled)} appointment(s).')
    for s in scheduled:
        print('-', s[0], s[2], '(', s[3], ')')

if __name__ == '__main__':
    main()
