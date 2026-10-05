-- MESSI: esquema MySQL 8.0.16 o posterior, con integridad InnoDB.
-- Se aplica desde scripts/init_database.py, no desde las pantallas.
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INT NOT NULL PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    applied_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
    id VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
    created_at VARCHAR(40) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    message VARCHAR(1000) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT requests_student FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT requests_message CHECK (CHAR_LENGTH(TRIM(message)) BETWEEN 1 AND 1000)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS supports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    support_type VARCHAR(40) NOT NULL,
    notes VARCHAR(1000) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pendiente',
    CONSTRAINT supports_student FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT supports_type CHECK (support_type IN ('Tutoria', 'Apoyo accesible', 'Orientacion')),
    CONSTRAINT supports_notes CHECK (CHAR_LENGTH(TRIM(notes)) BETWEEN 1 AND 1000),
    CONSTRAINT supports_status CHECK (status IN ('Pendiente', 'En seguimiento', 'Cerrado'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS followups (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    support_id BIGINT UNSIGNED NOT NULL,
    notes VARCHAR(1000) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT followups_support FOREIGN KEY (support_id) REFERENCES supports(id),
    CONSTRAINT followups_notes CHECK (CHAR_LENGTH(TRIM(notes)) BETWEEN 1 AND 1000),
    CONSTRAINT followups_status CHECK (status IN ('Pendiente', 'En seguimiento', 'Cerrado'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS indicators (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(12) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    period VARCHAR(64) NOT NULL,
    nota_parcial DOUBLE NOT NULL,
    asistencia DOUBLE NOT NULL,
    tareas_entregadas DOUBLE NOT NULL,
    updated_at VARCHAR(40) NOT NULL,
    CONSTRAINT indicators_student FOREIGN KEY (student_id) REFERENCES students(id),
    CONSTRAINT indicators_period UNIQUE (student_id, period),
    CONSTRAINT indicators_grade CHECK (nota_parcial BETWEEN 0 AND 10),
    CONSTRAINT indicators_attendance CHECK (asistencia BETWEEN 0 AND 100),
    CONSTRAINT indicators_homework CHECK (tareas_entregadas BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS predictions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    indicator_id BIGINT UNSIGNED NOT NULL,
    puntuacion_riesgo DOUBLE NOT NULL,
    alerta TINYINT NOT NULL,
    origen_modelo VARCHAR(100) NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    CONSTRAINT predictions_indicator FOREIGN KEY (indicator_id) REFERENCES indicators(id),
    CONSTRAINT predictions_unique_indicator UNIQUE (indicator_id),
    CONSTRAINT predictions_score CHECK (puntuacion_riesgo BETWEEN 0 AND 1),
    CONSTRAINT predictions_alert CHECK (alerta IN (0, 1))
) ENGINE=InnoDB;
