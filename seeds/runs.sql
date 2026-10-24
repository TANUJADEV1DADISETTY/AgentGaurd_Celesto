-- AgentGuard Run Ledger seed data
-- Idempotent: re-running will not duplicate the seed row.

CREATE TABLE IF NOT EXISTS runs (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL UNIQUE,
    sandbox_name    TEXT NOT NULL,
    problem_id      TEXT NOT NULL DEFAULT 'grading-task',
    state           TEXT NOT NULL CHECK (state IN ('created','ready','running','succeeded','failed','deleted')),
    execution_target TEXT NOT NULL DEFAULT 'celesto_sandbox',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ
);

-- Seed row (idempotent)
INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target, created_at)
VALUES (
    'seed-run-001',
    'sbx-seeddemo1',
    'grading-task',
    'deleted',
    'celesto_sandbox',
    NOW()
)
ON CONFLICT (run_id) DO NOTHING;
