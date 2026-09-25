-- LifeFlow: Blood Bank Management System
-- Database Schema: 3NF Relational Architecture with Composite Indexes
-- Target RDBMS: MySQL 8.0+

CREATE DATABASE IF NOT EXISTS lifeflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE lifeflow;

-- Table: users
-- Core authentication table for all 3 system roles (admin, donor, requester)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(191) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'donor', 'requester') NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: donors
-- Profile information for donors, linked 1:1 to users
CREATE TABLE IF NOT EXISTS donors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    date_of_birth DATE NOT NULL,
    last_donation_date DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_donors_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_donors_blood_type (blood_type),
    INDEX idx_donors_last_donation (last_donation_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: requesters
-- Profile information for requesting entities (hospitals, doctors, individuals)
CREATE TABLE IF NOT EXISTS requesters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    organization_name VARCHAR(150) NOT NULL,
    contact_phone VARCHAR(30) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_requesters_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: blood_units
-- Physical inventory units collected from donors
CREATE TABLE IF NOT EXISTS blood_units (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donation_id INT NULL,
    blood_type ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    collected_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    status ENUM('available', 'reserved', 'used', 'expired') NOT NULL DEFAULT 'available',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Composite index for fast inventory queries & row locking during fulfillment
    INDEX idx_blood_units_status_type (status, blood_type),
    INDEX idx_blood_units_expiry (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: donations
-- Log of all donation sessions performed by donors
CREATE TABLE IF NOT EXISTS donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    unit_id INT NULL,
    donated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes VARCHAR(255) NULL,
    CONSTRAINT fk_donations_donor FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE,
    CONSTRAINT fk_donations_unit FOREIGN KEY (unit_id) REFERENCES blood_units(id) ON DELETE SET NULL,
    INDEX idx_donations_donor_id (donor_id),
    INDEX idx_donations_donated_at (donated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Add deferred foreign key for blood_units -> donations
ALTER TABLE blood_units
    ADD CONSTRAINT fk_blood_units_donation FOREIGN KEY (donation_id) REFERENCES donations(id) ON DELETE SET NULL;

-- Table: blood_requests
-- Requests submitted by requesters, prioritized for admin approval
CREATE TABLE IF NOT EXISTS blood_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    requester_id INT NOT NULL,
    blood_type_requested ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    units_requested INT NOT NULL,
    urgency ENUM('critical', 'urgent', 'routine') NOT NULL DEFAULT 'routine',
    status ENUM('pending', 'approved', 'rejected', 'fulfilled') NOT NULL DEFAULT 'pending',
    rejection_reason VARCHAR(255) NULL,
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    resolved_by INT NULL,
    CONSTRAINT fk_requests_requester FOREIGN KEY (requester_id) REFERENCES requesters(id) ON DELETE CASCADE,
    CONSTRAINT fk_requests_resolved_by FOREIGN KEY (resolved_by) REFERENCES users(id) ON DELETE SET NULL,
    -- Composite index for urgency-driven queue queries
    INDEX idx_requests_queue (status, urgency, requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: request_fulfillments
-- Audit join table: maps which physical blood unit was allocated to which approved request.
-- UNIQUE constraint on unit_id guarantees a unit can NEVER be double-allocated.
CREATE TABLE IF NOT EXISTS request_fulfillments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    unit_id INT NOT NULL UNIQUE,
    allocated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fulfillments_request FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
    CONSTRAINT fk_fulfillments_unit FOREIGN KEY (unit_id) REFERENCES blood_units(id) ON DELETE RESTRICT,
    INDEX idx_fulfillments_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
