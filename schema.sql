CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    website TEXT,
    city TEXT,
    contact_name TEXT,
    contact_role TEXT,
    email TEXT,
    phone TEXT,
    company_type TEXT,
    relevant_topics TEXT,
    website_notes TEXT,
    pain_point_hypothesis TEXT,
    offer_angle TEXT,
    email_subject TEXT,
    email_body TEXT,
    email_variant TEXT,
    status TEXT DEFAULT 'Recherchiert',
    first_contact_date TEXT,
    follow_up_date TEXT,
    last_contact_date TEXT,
    response_type TEXT DEFAULT 'Keine Antwort',
    next_step TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);
CREATE INDEX IF NOT EXISTS idx_companies_follow_up_date ON companies(follow_up_date);
CREATE INDEX IF NOT EXISTS idx_companies_email ON companies(email);
CREATE INDEX IF NOT EXISTS idx_companies_name_website ON companies(company_name, website);
