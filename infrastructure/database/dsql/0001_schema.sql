CREATE SCHEMA app;

CREATE TABLE app.schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE app.users (
    user_sub VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    cognito_sub VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    student_active_session_id VARCHAR(64) NOT NULL DEFAULT '',
    given_name VARCHAR(50),
    family_name VARCHAR(50),
    country VARCHAR(100),
    profession VARCHAR(100),
    institution VARCHAR(200),
    research_interests TEXT,
    terms_accepted_at TIMESTAMPTZ,
    privacy_accepted_at TIMESTAMPTZ,
    pref_autoplay_next BOOLEAN NOT NULL DEFAULT TRUE,
    pref_auto_mark_complete BOOLEAN NOT NULL DEFAULT TRUE,
    pref_progress_celebrations BOOLEAN NOT NULL DEFAULT TRUE,
    research_interest_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_login_at TIMESTAMPTZ
);

CREATE TABLE app.courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by VARCHAR(255) NOT NULL,
    thumbnail_key VARCHAR(500) NOT NULL DEFAULT '',
    page_content JSONB NOT NULL DEFAULT '{}'::jsonb,
    price_amount_minor INTEGER,
    certificate_code CHAR(6) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT courses_created_by_not_blank CHECK (btrim(created_by) <> ''),
    CONSTRAINT courses_price_amount_minor_whole_jod CHECK (
        price_amount_minor IS NULL
        OR (price_amount_minor > 0 AND price_amount_minor % 1000 = 0)
    )
);

CREATE TABLE app.course_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    module_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (course_id, module_order),
    UNIQUE (course_id, id)
);

CREATE TABLE app.lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    module_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    lesson_order INTEGER NOT NULL,
    video_key VARCHAR(500) NOT NULL DEFAULT '',
    video_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    thumbnail_key VARCHAR(500) NOT NULL DEFAULT '',
    duration INTEGER NOT NULL DEFAULT 0,
    transcript TEXT,
    UNIQUE (course_id, module_id, lesson_order),
    UNIQUE (course_id, id),
    FOREIGN KEY (course_id, module_id) REFERENCES app.course_modules (course_id, id) ON DELETE CASCADE
);

CREATE TABLE app.lesson_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    lesson_id UUID NOT NULL,
    kind VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    object_key VARCHAR(500) NOT NULL DEFAULT '',
    content_type VARCHAR(100) NOT NULL DEFAULT '',
    byte_size BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT lesson_files_kind_check CHECK (kind IN ('resource', 'download')),
    CONSTRAINT lesson_files_status_check CHECK (status IN ('pending', 'ready')),
    CONSTRAINT lesson_files_byte_size_nonneg CHECK (byte_size >= 0),
    FOREIGN KEY (course_id, lesson_id) REFERENCES app.lessons (course_id, id) ON DELETE CASCADE
);

CREATE TABLE app.question_banks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    name VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT question_banks_status_valid CHECK (status IN ('DRAFT', 'PUBLISHED')),
    CONSTRAINT question_banks_name_non_empty
        CHECK (name IS NULL OR (length(btrim(name)) BETWEEN 1 AND 80)),
    UNIQUE (course_id, id)
);

CREATE TABLE app.module_quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    module_id UUID NOT NULL,
    question_bank_id UUID,
    served_count_n INTEGER,
    pass_percent INTEGER NOT NULL DEFAULT 70,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT module_quizzes_served_count_n_positive
        CHECK (served_count_n IS NULL OR served_count_n >= 1),
    CONSTRAINT module_quizzes_pass_percent_range
        CHECK (pass_percent >= 1 AND pass_percent <= 100),
    UNIQUE (module_id),
    UNIQUE (course_id, id),
    FOREIGN KEY (course_id, module_id) REFERENCES app.course_modules (course_id, id) ON DELETE CASCADE,
    FOREIGN KEY (course_id, question_bank_id) REFERENCES app.question_banks (course_id, id) ON DELETE RESTRICT
);

CREATE TABLE app.questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    question_bank_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    prompt_text TEXT NOT NULL DEFAULT '',
    options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    correct_option_key VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT questions_status_valid CHECK (status IN ('DRAFT', 'PUBLISHED')),
    FOREIGN KEY (course_id, question_bank_id) REFERENCES app.question_banks (course_id, id) ON DELETE CASCADE
);

CREATE TABLE app.student_module_quiz_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_quiz_id UUID NOT NULL REFERENCES app.module_quizzes(id) ON DELETE NO ACTION,
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE NO ACTION,
    user_sub VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (module_quiz_id, user_sub),
    FOREIGN KEY (course_id, module_quiz_id)
        REFERENCES app.module_quizzes (course_id, id) ON DELETE NO ACTION
);

CREATE TABLE app.student_module_quiz_binding_questions (
    binding_id UUID NOT NULL
        REFERENCES app.student_module_quiz_bindings(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    question_id UUID NOT NULL REFERENCES app.questions(id) ON DELETE NO ACTION,
    PRIMARY KEY (binding_id, position),
    UNIQUE (binding_id, question_id)
);

CREATE TABLE app.module_quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    binding_id UUID NOT NULL
        REFERENCES app.student_module_quiz_bindings(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL,
    shuffled_question_order JSONB NOT NULL,
    shuffled_choice_orders JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    UNIQUE (binding_id, attempt_number),
    CHECK (attempt_number >= 1),
    CHECK (status IN ('in_progress', 'submitted')),
    CHECK (jsonb_typeof(shuffled_question_order) = 'array'),
    CHECK (jsonb_typeof(shuffled_choice_orders) = 'object')
);

CREATE TABLE app.module_quiz_attempt_submissions (
    attempt_id UUID PRIMARY KEY
        REFERENCES app.module_quiz_attempts(id) ON DELETE CASCADE,
    answers_json JSONB NOT NULL,
    correct_count INTEGER NOT NULL,
    total_count INTEGER NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(answers_json) = 'object'),
    CHECK (total_count >= 1),
    CHECK (correct_count >= 0),
    CHECK (correct_count <= total_count)
);

CREATE TABLE app.assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE CASCADE,
    module_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    pass_percent INTEGER NOT NULL DEFAULT 70,
    counts_toward_certificate BOOLEAN NOT NULL DEFAULT FALSE,
    instructions_mode VARCHAR(20) NOT NULL DEFAULT 'plain',
    instructions_text TEXT NOT NULL DEFAULT '',
    instructions_html TEXT NOT NULL DEFAULT '',
    instructions_image_key VARCHAR(500) NOT NULL DEFAULT '',
    instructions_image_ready BOOLEAN NOT NULL DEFAULT FALSE,
    rubric_mode VARCHAR(20) NOT NULL DEFAULT 'plain',
    rubric_text TEXT NOT NULL DEFAULT '',
    rubric_html TEXT NOT NULL DEFAULT '',
    rubric_image_key VARCHAR(500) NOT NULL DEFAULT '',
    rubric_image_ready BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assignments_status_check CHECK (status IN ('draft', 'published')),
    CONSTRAINT assignments_pass_percent_check CHECK (pass_percent >= 1 AND pass_percent <= 100),
    CONSTRAINT assignments_instructions_mode_check CHECK (
        instructions_mode IN ('plain', 'rich', 'image')
    ),
    CONSTRAINT assignments_rubric_mode_check CHECK (
        rubric_mode IN ('plain', 'rich', 'image')
    ),
    FOREIGN KEY (course_id, module_id)
        REFERENCES app.course_modules (course_id, id) ON DELETE CASCADE
);

CREATE TABLE app.assignment_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES app.assignments(id) ON DELETE CASCADE,
    label VARCHAR(120) NOT NULL,
    max_points INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_criteria_max_points_check CHECK (max_points >= 1 AND max_points <= 100)
);

CREATE TABLE app.assignment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES app.assignments(id) ON DELETE NO ACTION,
    course_id UUID NOT NULL,
    user_sub VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    CONSTRAINT assignment_submissions_status_check CHECK (
        status IN ('draft', 'submitted', 'graded')
    )
);

CREATE TABLE app.assignment_submission_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES app.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES app.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    object_key VARCHAR(500) NOT NULL DEFAULT '',
    content_type VARCHAR(100) NOT NULL DEFAULT '',
    byte_size BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_submission_files_status_check CHECK (
        status IN ('pending', 'ready')
    ),
    CONSTRAINT assignment_submission_files_byte_size_nonneg CHECK (byte_size >= 0),
    CONSTRAINT assignment_submission_files_type_check CHECK (
        file_type IN ('pdf', 'csv', 'xlsx', 'docx', 'sav')
    )
);

CREATE TABLE app.assignment_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL UNIQUE REFERENCES app.assignment_submissions(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES app.assignments(id) ON DELETE CASCADE,
    course_id UUID NOT NULL,
    score_percent INTEGER NOT NULL,
    pass_percent INTEGER NOT NULL,
    passed BOOLEAN NOT NULL,
    feedback TEXT NOT NULL,
    graded_by VARCHAR(255) NOT NULL,
    graded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT assignment_grades_score_percent_check CHECK (
        score_percent >= 0 AND score_percent <= 100
    ),
    CONSTRAINT assignment_grades_pass_percent_check CHECK (
        pass_percent >= 1 AND pass_percent <= 100
    )
);

CREATE TABLE app.assignment_grade_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grade_id UUID NOT NULL REFERENCES app.assignment_grades(id) ON DELETE CASCADE,
    criterion_id UUID NOT NULL REFERENCES app.assignment_criteria(id) ON DELETE CASCADE,
    points INTEGER NOT NULL,
    CONSTRAINT assignment_grade_scores_points_nonneg CHECK (points >= 0),
    CONSTRAINT assignment_grade_scores_unique UNIQUE (grade_id, criterion_id)
);

CREATE TABLE app.enrollments (
    user_sub VARCHAR(255) NOT NULL REFERENCES app.users(user_sub) ON DELETE NO ACTION,
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE NO ACTION,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source VARCHAR(50) NOT NULL DEFAULT 'self_service',
    PRIMARY KEY (user_sub, course_id)
);

CREATE TABLE app.lesson_progress (
    user_sub VARCHAR(255) NOT NULL REFERENCES app.users(user_sub) ON DELETE NO ACTION,
    lesson_id UUID NOT NULL,
    course_id UUID NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    last_position_sec INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_sub, lesson_id),
    CONSTRAINT chk_lesson_progress_position_nonneg CHECK (last_position_sec >= 0),
    CONSTRAINT lesson_progress_course_lesson_fkey
        FOREIGN KEY (course_id, lesson_id) REFERENCES app.lessons (course_id, id) ON DELETE NO ACTION,
    FOREIGN KEY (course_id) REFERENCES app.courses (id) ON DELETE NO ACTION
);

CREATE TABLE app.lesson_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_sub VARCHAR(255) NOT NULL REFERENCES app.users(user_sub) ON DELETE NO ACTION,
    course_id UUID NOT NULL,
    lesson_id UUID NOT NULL,
    body TEXT NOT NULL,
    timestamp_sec INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT lesson_notes_timestamp_range CHECK (
        timestamp_sec IS NULL OR (timestamp_sec >= 0 AND timestamp_sec <= 86400)
    ),
    FOREIGN KEY (course_id, lesson_id) REFERENCES app.lessons (course_id, id) ON DELETE NO ACTION
);

CREATE TABLE app.learning_activity_days (
    user_sub VARCHAR(255) NOT NULL REFERENCES app.users(user_sub) ON DELETE NO ACTION,
    day DATE NOT NULL,
    PRIMARY KEY (user_sub, day)
);

CREATE TABLE app.research_team_required_courses (
    course_id UUID PRIMARY KEY REFERENCES app.courses(id) ON DELETE CASCADE
);

CREATE TABLE app.bundle_offers (
    environment VARCHAR(32) PRIMARY KEY,
    amount_minor INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'JOD',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT bundle_offers_amount_minor_whole_jod
        CHECK (amount_minor > 0 AND amount_minor % 1000 = 0)
);

CREATE TABLE app.rate_limit_counters (
    bucket_key TEXT PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL,
    count INT NOT NULL,
    CHECK (count >= 0)
);

CREATE TABLE app.payment_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment VARCHAR(32) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    provider_event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    payload_digest VARCHAR(128),
    UNIQUE (provider, provider_event_id)
);

CREATE TABLE app.purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_sub VARCHAR(255) NOT NULL REFERENCES app.users(user_sub) ON DELETE NO ACTION,
    environment VARCHAR(32) NOT NULL,
    product_type VARCHAR(16) NOT NULL,
    course_id UUID,
    status VARCHAR(32) NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'JOD',
    provider VARCHAR(32) NOT NULL DEFAULT 'hyperpay',
    provider_tran_ref VARCHAR(255),
    cart_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT purchases_product_type_valid
        CHECK (product_type IN ('course', 'bundle')),
    CONSTRAINT purchases_status_valid
        CHECK (status IN ('pending', 'paid', 'revoked', 'failed')),
    CONSTRAINT purchases_amount_minor_whole_jod CHECK (amount_minor > 0 AND amount_minor % 1000 = 0),
    CONSTRAINT purchases_course_product_requires_course_id
        CHECK (
            (product_type = 'course' AND course_id IS NOT NULL)
            OR (product_type = 'bundle' AND course_id IS NULL)
        ),
    CONSTRAINT purchases_course_id_fkey
        FOREIGN KEY (course_id) REFERENCES app.courses (id) ON DELETE NO ACTION
);

CREATE TABLE app.certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_sub VARCHAR(255) NOT NULL,
    course_id UUID NOT NULL REFERENCES app.courses(id) ON DELETE NO ACTION,
    credential_id VARCHAR(64) NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    course_title VARCHAR(255) NOT NULL,
    issue_date DATE NOT NULL,
    instructor_name VARCHAR(255) NOT NULL,
    instructor_title VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT certificates_status_check CHECK (status IN ('valid', 'revoked')),
    CONSTRAINT certificates_credential_id_key UNIQUE (credential_id),
    CONSTRAINT certificates_user_course_key UNIQUE (user_sub, course_id)
);

CREATE TABLE app.bundle_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_sub VARCHAR(255) NOT NULL,
    credential_id VARCHAR(64) NOT NULL,
    student_name VARCHAR(255) NOT NULL,
    issue_date DATE NOT NULL,
    instructor_name VARCHAR(255) NOT NULL,
    instructor_title VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT bundle_certificates_status_check CHECK (status IN ('valid', 'revoked')),
    CONSTRAINT bundle_certificates_credential_id_key UNIQUE (credential_id),
    CONSTRAINT bundle_certificates_user_sub_key UNIQUE (user_sub)
);

CREATE TABLE app.research_team_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_sub VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    reapply_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(320) NOT NULL,
    country VARCHAR(100) NOT NULL,
    institution VARCHAR(200) NOT NULL,
    position VARCHAR(200) NOT NULL,
    publication_count INT NOT NULL,
    project_count INT NOT NULL,
    stats_experience VARCHAR(32) NOT NULL,
    sys_review_experience VARCHAR(32) NOT NULL,
    research_areas JSONB NOT NULL DEFAULT '[]'::jsonb,
    interests TEXT NOT NULL,
    motivation TEXT NOT NULL,
    weekly_hours VARCHAR(64) NOT NULL,
    acknowledged_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT research_team_applications_status_check
        CHECK (status IN ('submitted', 'under_review', 'accepted', 'rejected')),
    CONSTRAINT research_team_applications_publication_count_check
        CHECK (publication_count >= 0 AND publication_count <= 9999),
    CONSTRAINT research_team_applications_project_count_check
        CHECK (project_count >= 0 AND project_count <= 9999)
);

CREATE INDEX ASYNC idx_courses_status ON app.courses (status);

CREATE INDEX ASYNC idx_courses_created_by ON app.courses (created_by);

CREATE UNIQUE INDEX ASYNC courses_certificate_code_key ON app.courses (certificate_code);

CREATE INDEX ASYNC idx_course_modules_course_order ON app.course_modules (course_id, module_order);

CREATE INDEX ASYNC idx_lessons_course_module_order ON app.lessons (course_id, module_id, lesson_order);

CREATE INDEX ASYNC idx_lesson_files_lesson ON app.lesson_files (course_id, lesson_id);

CREATE INDEX ASYNC idx_question_banks_course_id ON app.question_banks (course_id);

CREATE INDEX ASYNC idx_module_quizzes_course_id ON app.module_quizzes (course_id);

CREATE INDEX ASYNC idx_module_quizzes_question_bank_id ON app.module_quizzes (question_bank_id);

CREATE UNIQUE INDEX ASYNC uq_module_quizzes_course_question_bank ON app.module_quizzes (course_id, question_bank_id) WHERE question_bank_id IS NOT NULL;

CREATE INDEX ASYNC idx_questions_course_bank ON app.questions (course_id, question_bank_id);

CREATE INDEX ASYNC idx_questions_bank_status ON app.questions (question_bank_id, status);

CREATE INDEX ASYNC idx_student_module_quiz_bindings_course_user ON app.student_module_quiz_bindings (course_id, user_sub);

CREATE UNIQUE INDEX ASYNC uq_module_quiz_attempts_one_in_progress ON app.module_quiz_attempts (binding_id) WHERE status = 'in_progress';

CREATE INDEX ASYNC idx_assignments_course ON app.assignments (course_id);

CREATE INDEX ASYNC idx_assignments_course_module ON app.assignments (course_id, module_id);

CREATE INDEX ASYNC idx_assignment_criteria_assignment ON app.assignment_criteria (assignment_id, sort_order);

CREATE INDEX ASYNC idx_assignment_submissions_assignment_user ON app.assignment_submissions (assignment_id, user_sub);

CREATE UNIQUE INDEX ASYNC assignment_submissions_one_draft_per_user ON app.assignment_submissions (assignment_id, user_sub) WHERE status = 'draft';

CREATE INDEX ASYNC idx_assignment_submission_files_submission ON app.assignment_submission_files (submission_id);

CREATE INDEX ASYNC idx_assignment_grade_scores_grade ON app.assignment_grade_scores (grade_id);

CREATE INDEX ASYNC idx_enrollments_course ON app.enrollments (course_id);

CREATE INDEX ASYNC idx_lesson_progress_course_user ON app.lesson_progress (course_id, user_sub);

CREATE INDEX ASYNC idx_lesson_notes_user_lesson ON app.lesson_notes (user_sub, lesson_id);

CREATE INDEX ASYNC idx_purchases_user_env ON app.purchases (user_sub, environment);

CREATE INDEX ASYNC idx_purchases_provider_tran_ref ON app.purchases (provider, provider_tran_ref) WHERE provider_tran_ref IS NOT NULL;

CREATE UNIQUE INDEX ASYNC uq_purchases_one_paid_course_per_user_course_env ON app.purchases (user_sub, course_id, environment) WHERE product_type = 'course' AND status = 'paid';

CREATE UNIQUE INDEX ASYNC uq_purchases_one_paid_bundle_per_user_env ON app.purchases (user_sub, environment) WHERE product_type = 'bundle' AND status = 'paid';

CREATE INDEX ASYNC idx_payment_webhook_events_environment_received ON app.payment_webhook_events (environment, received_at);

CREATE INDEX ASYNC idx_certificates_course ON app.certificates (course_id);

CREATE INDEX ASYNC idx_certificates_user ON app.certificates (user_sub);

CREATE UNIQUE INDEX ASYNC certificates_credential_id_upper ON app.certificates ((upper(credential_id)));

CREATE INDEX ASYNC idx_bundle_certificates_user ON app.bundle_certificates (user_sub);

CREATE UNIQUE INDEX ASYNC research_team_applications_one_open ON app.research_team_applications (user_sub) WHERE status IN ('submitted', 'under_review');

CREATE UNIQUE INDEX ASYNC research_team_applications_one_accepted ON app.research_team_applications (user_sub) WHERE status = 'accepted';

CREATE INDEX ASYNC idx_research_team_applications_user ON app.research_team_applications (user_sub);

CREATE INDEX ASYNC idx_research_team_applications_status ON app.research_team_applications (status);

INSERT INTO app.bundle_offers (environment, amount_minor, currency, active) VALUES ('prod', 150000, 'JOD', TRUE) ON CONFLICT (environment) DO NOTHING;

INSERT INTO app.schema_migrations (version) VALUES ('0001') ON CONFLICT (version) DO NOTHING;
