CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    usn VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(512) NOT NULL,
    original_name VARCHAR(512) NOT NULL,
    content_type VARCHAR(128),
    file_type VARCHAR(32) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    extracted_text TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    source_type VARCHAR(32) NOT NULL DEFAULT 'upload',
    source_message_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    student_name VARCHAR(255),
    usn VARCHAR(32),
    subject VARCHAR(255),
    subject_code VARCHAR(32),
    subject_name VARCHAR(255),
    grade VARCHAR(32),
    grade_points DOUBLE PRECISION,
    sgpa DOUBLE PRECISION,
    raw_text TEXT,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'partial',
    validation_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    subject VARCHAR(512),
    sender VARCHAR(255),
    received_at VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'fetched',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
