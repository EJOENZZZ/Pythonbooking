-- ═══════════════════════════════════════════════════════════════
--  TRAVELBOOK DATABASE SCHEMA
--  Run this in: Supabase → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════════


-- ── 1. USERS TABLE ────────────────────────────────────────────
create table if not exists users (
  id          uuid primary key default gen_random_uuid(),
  full_name   text not null,
  email       text not null unique,
  password    text not null,
  is_admin    boolean default false,
  created_at  timestamp default now()
);

-- Default admin account (username: admin, password: 1234)
insert into users (full_name, email, password, is_admin) values
  ('Admin', 'admin', encode(sha256('1234'), 'hex'), true)
on conflict (email) do nothing;

create index if not exists idx_users_email on users(email);

alter table users enable row level security;
create policy "Public can insert users" on users for insert with check (true);
create policy "Public can select users" on users for select using (true);


-- ── 2. TRIPS TABLE ────────────────────────────────────────────
create table if not exists trips (
  id          text primary key,
  type        text not null check (type in ('plane', 'ferry')),
  from_city   text not null,
  to_city     text not null,
  departure   timestamp not null,
  arrival     timestamp not null,
  operator    text not null,
  price       numeric(10,2) not null check (price >= 0),
  seats       int not null check (seats >= 0),
  created_at  timestamp default now()
);

alter table trips enable row level security;
create policy "Public can view trips" on trips for select using (true);
create policy "Public can update trips" on trips for update using (true);


-- ── 3. RESET CODES TABLE ─────────────────────────────────────────
create table if not exists reset_codes (
  email      text primary key,
  code       text not null,
  created_at timestamp default now()
);
alter table reset_codes enable row level security;
create policy "Public reset_codes" on reset_codes using (true) with check (true);


-- ── 4. BOOKINGS TABLE ─────────────────────────────────────────
create table if not exists bookings (
  id              text primary key,
  trip_id         text not null references trips(id) on delete restrict,
  user_id         uuid references users(id) on delete set null,
  type            text not null check (type in ('plane', 'ferry')),
  from_city       text not null,
  to_city         text not null,
  departure       timestamp not null,
  arrival         timestamp not null,
  operator        text not null,
  passenger_name  text not null,
  email           text not null,
  phone           text not null,
  passengers      int not null check (passengers >= 1),
  total           numeric(10,2) not null check (total >= 0),
  status          text not null default 'Confirmed' check (status in ('Confirmed', 'Cancelled', 'Pending Cancellation')),
  cancel_reason   text,
  booked_at       timestamp default now()
);

create index if not exists idx_bookings_trip_id on bookings(trip_id);
create index if not exists idx_bookings_user_id on bookings(user_id);
create index if not exists idx_bookings_email   on bookings(email);
create index if not exists idx_bookings_status  on bookings(status);
create index if not exists idx_trips_type       on trips(type);
create index if not exists idx_trips_from_to    on trips(from_city, to_city);

alter table bookings enable row level security;
create policy "Public can view bookings"   on bookings for select using (true);
create policy "Public can insert bookings" on bookings for insert with check (true);
create policy "Public can delete bookings" on bookings for delete using (true);
create policy "Public can update bookings" on bookings for update using (true);


-- ── 4. SEED TRIPS DATA ────────────────────────────────────────
insert into trips (id, type, from_city, to_city, departure, arrival, operator, price, seats) values
  -- Flights
  ('F1', 'plane','Manila',   'Cebu',      '2025-08-10 06:00','2025-08-10 07:10','Cebu Pacific',        2500.00,120),
  ('F2', 'plane','Manila',   'Davao',     '2025-08-10 08:00','2025-08-10 09:30','Philippine Airlines', 3200.00,100),
  ('F3', 'plane','Manila',   'Iloilo',    '2025-08-10 07:00','2025-08-10 08:00','Philippine Airlines', 2800.00,110),
  ('F4', 'plane','Manila',   'Bacolod',   '2025-08-10 09:00','2025-08-10 10:00','AirAsia Philippines', 2600.00,100),
  ('F5', 'plane','Manila',   'Cagayan de Oro','2025-08-10 10:00','2025-08-10 11:30','Cebu Pacific',    3000.00,100),
  ('F6', 'plane','Manila',   'Zamboanga', '2025-08-10 11:00','2025-08-10 12:30','Philippine Airlines', 3500.00, 90),
  ('F7', 'plane','Manila',   'Dumaguete', '2025-08-10 12:00','2025-08-10 13:10','Cebu Pacific',        2700.00, 90),
  ('F8', 'plane','Cebu',     'Manila',    '2025-08-11 14:00','2025-08-11 15:10','Cebu Pacific',        2600.00, 90),
  ('F9', 'plane','Cebu',     'Davao',     '2025-08-11 07:00','2025-08-11 08:10','Cebu Pacific',        2200.00, 90),
  ('F10','plane','Cebu',     'Iloilo',    '2025-08-11 09:00','2025-08-11 09:50','AirAsia Philippines', 2100.00, 80),
  ('F11','plane','Davao',    'Manila',    '2025-08-12 10:00','2025-08-12 11:30','AirAsia Philippines', 3100.00, 80),
  ('F12','plane','Davao',    'Cebu',      '2025-08-12 08:00','2025-08-12 09:10','Cebu Pacific',        2200.00, 80),
  ('F13','plane','Iloilo',   'Manila',    '2025-08-13 15:00','2025-08-13 16:00','Cebu Pacific',        2750.00, 95),
  ('F14','plane','Iloilo',   'Cebu',      '2025-08-13 09:00','2025-08-13 09:50','AirAsia Philippines', 2000.00, 80),
  ('F15','plane','Bacolod',  'Manila',    '2025-08-13 06:00','2025-08-13 07:00','Cebu Pacific',        2600.00, 90),
  ('F16','plane','Bacolod',  'Cebu',      '2025-08-13 10:00','2025-08-13 10:50','AirAsia Philippines', 1900.00, 80),
  ('F17','plane','Cagayan de Oro','Manila','2025-08-14 07:00','2025-08-14 08:30','Philippine Airlines',3000.00, 90),
  ('F18','plane','Cagayan de Oro','Cebu', '2025-08-14 09:00','2025-08-14 09:50','Cebu Pacific',        1800.00, 80),
  ('F19','plane','Zamboanga','Manila',    '2025-08-14 06:00','2025-08-14 07:30','Philippine Airlines', 3500.00, 80),
  ('F20','plane','Dumaguete','Manila',    '2025-08-14 08:00','2025-08-14 09:10','Cebu Pacific',        2700.00, 80),
  -- Ferries
  ('V1', 'ferry','Batangas', 'Calapan',   '2025-08-10 07:00','2025-08-10 09:00','Oceanjet',   350.00,200),
  ('V2', 'ferry','Calapan',  'Batangas',  '2025-08-10 12:00','2025-08-10 14:00','Oceanjet',   350.00,200),
  ('V3', 'ferry','Manila',   'Batangas',  '2025-08-10 06:00','2025-08-10 09:00','2GO Travel', 500.00,180),
  ('V4', 'ferry','Batangas', 'Manila',    '2025-08-10 15:00','2025-08-10 18:00','2GO Travel', 500.00,180),
  ('V5', 'ferry','Manila',   'Calapan',   '2025-08-10 08:00','2025-08-10 11:00','2GO Travel', 450.00,180),
  ('V6', 'ferry','Calapan',  'Manila',    '2025-08-10 13:00','2025-08-10 16:00','Oceanjet',   450.00,180),
  ('V7', 'ferry','Cebu',     'Dumaguete', '2025-08-11 09:00','2025-08-11 11:30','SuperCat',   320.00,140),
  ('V8', 'ferry','Dumaguete','Cebu',      '2025-08-11 13:00','2025-08-11 15:30','Oceanjet',   310.00,140),
  ('V9', 'ferry','Cebu',     'Iloilo',    '2025-08-11 08:00','2025-08-11 12:00','SuperCat',   400.00,150),
  ('V10','ferry','Iloilo',   'Cebu',      '2025-08-11 14:00','2025-08-11 18:00','SuperCat',   400.00,150),
  ('V11','ferry','Manila',   'Cebu',      '2025-08-12 18:00','2025-08-13 06:00','2GO Travel', 900.00,200),
  ('V12','ferry','Cebu',     'Manila',    '2025-08-13 18:00','2025-08-14 06:00','2GO Travel', 900.00,200),
  ('V13','ferry','Batangas', 'Calapan',   '2025-08-12 07:00','2025-08-12 09:00','SuperCat',   350.00,180),
  ('V14','ferry','Dumaguete','Bacolod',   '2025-08-12 08:00','2025-08-12 10:00','Oceanjet',   280.00,140),
  ('V15','ferry','Bacolod',  'Dumaguete', '2025-08-12 13:00','2025-08-12 15:00','Oceanjet',   280.00,140)
on conflict (id) do nothing;
