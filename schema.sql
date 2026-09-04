CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('farmer','staff','admin')),
  password_hash TEXT NOT NULL,
  farmer_registration_id TEXT UNIQUE,
  village TEXT,
  land_acres REAL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS centres (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  district TEXT NOT NULL,
  address TEXT NOT NULL,
  staff_user_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS commodities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  min_quantity REAL NOT NULL,
  max_quantity REAL NOT NULL,
  required_docs TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  centre_id INTEGER NOT NULL REFERENCES centres(id),
  commodity_id INTEGER NOT NULL REFERENCES commodities(id),
  procurement_date TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  slot_minutes INTEGER NOT NULL DEFAULT 10,
  capacity INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','closed','completed'))
);

CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_number TEXT NOT NULL UNIQUE,
  farmer_id INTEGER NOT NULL REFERENCES users(id),
  schedule_id INTEGER NOT NULL REFERENCES schedules(id),
  quantity REAL NOT NULL,
  eligibility_status TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('booked','checked_in','serving','completed','cancelled','no_show')),
  queue_position INTEGER NOT NULL,
  booked_at TEXT NOT NULL,
  checkin_at TEXT,
  service_started_at TEXT,
  completed_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  channel TEXT NOT NULL,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  delivery_status TEXT NOT NULL,
  error_message TEXT,
  created_at TEXT NOT NULL,
  sent_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id INTEGER,
  details TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_schedules_date_status ON schedules(procurement_date, status);
CREATE INDEX IF NOT EXISTS idx_bookings_schedule_queue ON bookings(schedule_id, queue_position);
CREATE INDEX IF NOT EXISTS idx_bookings_farmer_status ON bookings(farmer_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC);
PRAGMA optimize;

