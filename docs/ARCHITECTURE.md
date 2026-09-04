# ProcureFlow architecture

## Runtime

```text
Browser
  |
  v
Flask routes + Jinja templates
  |-- role and CSRF checks
  |-- eligibility and capacity rules
  |-- queue state machine
  |-- notification service ----> Gmail SMTP (optional)
  |
  v
SQLite database
  |-- users / centres / commodities
  |-- schedules / bookings
  |-- notifications / audit_logs
```

## Booking state machine

```text
booked -> checked_in -> serving -> completed
   |          |
   +-> cancelled
   +-> no_show
```

Invalid state transitions are rejected server-side. A schedule's capacity is calculated from non-cancelled, non-no-show bookings. Duplicate active bookings by one farmer for the same schedule are blocked.

## Automated messages

- Booking creation: token confirmation.
- Farmer cancellation: cancellation status message.
- Staff check-in/start/complete: status update.
- Daily command: next-day procurement reminder.

Every message is first represented as an application record. SMTP delivery is an optional delivery channel rather than the source of truth.

