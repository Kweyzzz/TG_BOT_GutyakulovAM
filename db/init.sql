CREATE USER bot_user WITH PASSWORD 'amal88824';

CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE phone_numbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) NOT NULL
);

GRANT ALL PRIVILEGES ON TABLE emails, phone_numbers TO bot_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bot_user;

INSERT INTO emails (email) VALUES
    ('test@mail.com'),
    ('amal@mail.ru');

INSERT INTO phone_numbers (phone_number) VALUES
    ('+79991234567'),
    ('8-932-334-22-41');
