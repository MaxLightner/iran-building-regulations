-- PostgreSQL 16+. Dates retain their original calendar text; unknown != effective now.
CREATE TABLE sources (
 id text PRIMARY KEY, name text NOT NULL, official_base_url text NOT NULL,
 authority_type text NOT NULL, redistribution_status text NOT NULL DEFAULT 'unknown',
 checked_at timestamptz, notes text
);
CREATE TABLE documents (
 id text PRIMARY KEY, source_id text NOT NULL REFERENCES sources(id),
 mabhas_number integer CHECK (mabhas_number > 0), title text NOT NULL,
 kind text NOT NULL CHECK (kind IN ('regulation','erratum','notification','appendix','guide','draft')),
 official_page_url text NOT NULL, parent_document_id text REFERENCES documents(id),
 verification_status text NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','approved','rejected')),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE editions (
 id text PRIMARY KEY, document_id text NOT NULL REFERENCES documents(id), label text,
 edition_number integer, edition_year_text text,
 publication_date date, publication_date_text text, publication_calendar text,
 effective_date date, effective_date_text text,
 effective_date_status text NOT NULL DEFAULT 'unknown' CHECK (effective_date_status IN ('unknown','documented','conditional','disputed')),
 effective_date_evidence text, transition_conditions jsonb,
 official_pdf_url text, sha256 text CHECK (sha256 ~ '^[a-f0-9]{64}$'), private_storage_key text,
 validity_status text NOT NULL DEFAULT 'unconfirmed' CHECK (validity_status IN ('unconfirmed','current','superseded','withdrawn','draft')),
 verification_status text NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','approved','rejected')),
 supersedes_id text REFERENCES editions(id), verified_by text, verified_at timestamptz,
 CHECK (effective_date_status <> 'documented' OR effective_date_evidence IS NOT NULL),
 CHECK (verification_status <> 'approved' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL))
);
CREATE TABLE sections (
 id text PRIMARY KEY, edition_id text NOT NULL REFERENCES editions(id),
 parent_id text REFERENCES sections(id), title text NOT NULL, locator text, sort_order integer,
 UNIQUE(id, edition_id)
);
CREATE TABLE clauses (
 id text PRIMARY KEY, edition_id text NOT NULL REFERENCES editions(id), section_id text,
 stable_key text NOT NULL, kind text NOT NULL CHECK (kind IN ('clause','table','note','figure','appendix')),
 title text, original_text text NOT NULL, search_text text NOT NULL,
 locator text, pdf_page integer CHECK (pdf_page > 0), printed_page text,
 bounding_box jsonb, structured_content jsonb, extraction_method text, extraction_confidence numeric CHECK(extraction_confidence BETWEEN 0 AND 1),
 verification_status text NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','approved','rejected')),
 verified_by text, verified_at timestamptz, updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (section_id,edition_id) REFERENCES sections(id,edition_id),
 UNIQUE(edition_id,stable_key),
 CHECK (verification_status <> 'approved' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL AND locator IS NOT NULL AND pdf_page IS NOT NULL))
);
CREATE TABLE tags (id text PRIMARY KEY, name text NOT NULL UNIQUE);
CREATE TABLE clause_tags (clause_id text REFERENCES clauses(id), tag_id text REFERENCES tags(id), PRIMARY KEY(clause_id,tag_id));
CREATE TABLE clause_references (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, from_clause_id text NOT NULL REFERENCES clauses(id),
 to_clause_id text REFERENCES clauses(id), unresolved_reference text, relation text NOT NULL,
 CHECK (to_clause_id IS NOT NULL OR unresolved_reference IS NOT NULL)
);
CREATE TABLE applicability_conditions (
 id text PRIMARY KEY, clause_id text NOT NULL REFERENCES clauses(id),
 condition jsonb NOT NULL, evidence_locator text NOT NULL,
 verification_status text NOT NULL DEFAULT 'pending', notes text
);
CREATE TABLE clause_revisions (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 old_clause_id text REFERENCES clauses(id), new_clause_id text REFERENCES clauses(id),
 change_type text NOT NULL CHECK (change_type IN ('added','removed','modified','renumbered','split','merged','table_changed','note_changed')),
 evidence_document_id text REFERENCES documents(id), comparison_notes text,
 verification_status text NOT NULL DEFAULT 'pending', reviewed_by text, reviewed_at timestamptz,
 CHECK (old_clause_id IS NOT NULL OR new_clause_id IS NOT NULL)
);
CREATE TABLE source_checks (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, source_id text REFERENCES sources(id),
 edition_id text REFERENCES editions(id), url text NOT NULL, final_url text,
 checked_at timestamptz NOT NULL DEFAULT now(), http_status integer,
 observed_sha256 text CHECK (observed_sha256 ~ '^[a-f0-9]{64}$'), previous_sha256 text,
 result text NOT NULL, error text, etag text, last_modified text
);
CREATE TABLE topics (
 id text PRIMARY KEY, title text NOT NULL, summary text, key_factors jsonb,
 verification_status text NOT NULL DEFAULT 'pending', updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE topic_clauses (topic_id text REFERENCES topics(id), clause_id text REFERENCES clauses(id), PRIMARY KEY(topic_id,clause_id));
CREATE INDEX clauses_edition_idx ON clauses(edition_id);
CREATE INDEX clauses_search_idx ON clauses(search_text text_pattern_ops);
CREATE INDEX source_checks_url_time_idx ON source_checks(url,checked_at DESC);
-- No clauses, conditions, summaries or engineering values are seeded.

