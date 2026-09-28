"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-27 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='USER'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 2. Diagnostic Centres
    op.create_table(
        'diagnostic_centres',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('pincode', sa.String(length=20), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_diagnostic_centres'))
    )
    op.create_index(op.f('ix_diagnostic_centres_city'), 'diagnostic_centres', ['city'], unique=False)
    op.create_index(op.f('ix_diagnostic_centres_id'), 'diagnostic_centres', ['id'], unique=False)
    op.create_index(op.f('ix_diagnostic_centres_is_active'), 'diagnostic_centres', ['is_active'], unique=False)

    # 3. Diagnostic Tests
    op.create_table(
        'diagnostic_tests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('preparation_instructions', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_diagnostic_tests'))
    )
    op.create_index(op.f('ix_diagnostic_tests_code'), 'diagnostic_tests', ['code'], unique=True)
    op.create_index(op.f('ix_diagnostic_tests_category'), 'diagnostic_tests', ['category'], unique=False)
    op.create_index(op.f('ix_diagnostic_tests_id'), 'diagnostic_tests', ['id'], unique=False)
    op.create_index(op.f('ix_diagnostic_tests_is_active'), 'diagnostic_tests', ['is_active'], unique=False)

    # 4. Centre Test Offerings
    op.create_table(
        'centre_test_offerings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('centre_id', sa.UUID(), nullable=False),
        sa.Column('test_id', sa.UUID(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['centre_id'], ['diagnostic_centres.id'], name=op.f('fk_centre_test_offerings_centre_id_diagnostic_centres'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_id'], ['diagnostic_tests.id'], name=op.f('fk_centre_test_offerings_test_id_diagnostic_tests'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_centre_test_offerings')),
        sa.UniqueConstraint('centre_id', 'test_id', name='uq_centre_test_offering')
    )
    op.create_index(op.f('ix_centre_test_offerings_centre_id'), 'centre_test_offerings', ['centre_id'], unique=False)
    op.create_index(op.f('ix_centre_test_offerings_test_id'), 'centre_test_offerings', ['test_id'], unique=False)
    op.create_index(op.f('ix_centre_test_offerings_id'), 'centre_test_offerings', ['id'], unique=False)

    # 5. Bookings
    op.create_table(
        'bookings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('booking_reference', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('centre_id', sa.UUID(), nullable=False),
        sa.Column('test_id', sa.UUID(), nullable=False),
        sa.Column('offering_id', sa.UUID(), nullable=False),
        sa.Column('appointment_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['centre_id'], ['diagnostic_centres.id'], name=op.f('fk_bookings_centre_id_diagnostic_centres')),
        sa.ForeignKeyConstraint(['offering_id'], ['centre_test_offerings.id'], name=op.f('fk_bookings_offering_id_centre_test_offerings')),
        sa.ForeignKeyConstraint(['test_id'], ['diagnostic_tests.id'], name=op.f('fk_bookings_test_id_diagnostic_tests')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bookings_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bookings'))
    )
    op.create_index(op.f('ix_bookings_booking_reference'), 'bookings', ['booking_reference'], unique=True)
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
    op.create_index(op.f('ix_bookings_status'), 'bookings', ['status'], unique=False)
    op.create_index(op.f('ix_bookings_user_id'), 'bookings', ['user_id'], unique=False)
    op.create_index('ix_bookings_user_idempotency', 'bookings', ['user_id', 'idempotency_key'], unique=True)

    # 6. Booking Status History
    op.create_table(
        'booking_status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('booking_id', sa.UUID(), nullable=False),
        sa.Column('previous_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_booking_status_history_booking_id_bookings'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_booking_status_history_changed_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_booking_status_history'))
    )
    op.create_index(op.f('ix_booking_status_history_booking_id'), 'booking_status_history', ['booking_id'], unique=False)

    # 7. Payments
    op.create_table(
        'payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('booking_id', sa.UUID(), nullable=False),
        sa.Column('provider_payment_id', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_payments_booking_id_bookings')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_payments'))
    )
    op.create_index(op.f('ix_payments_provider_payment_id'), 'payments', ['provider_payment_id'], unique=True)
    op.create_index(op.f('ix_payments_booking_id'), 'payments', ['booking_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)

    # 8. Webhook Events
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='mock_gateway'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processing_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_webhook_events'))
    )
    op.create_index(op.f('ix_webhook_events_event_id'), 'webhook_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_webhook_events_processing_status'), 'webhook_events', ['processing_status'], unique=False)


def downgrade() -> None:
    op.drop_table('webhook_events')
    op.drop_table('payments')
    op.drop_table('booking_status_history')
    op.drop_table('bookings')
    op.drop_table('centre_test_offerings')
    op.drop_table('diagnostic_tests')
    op.drop_table('diagnostic_centres')
    op.drop_table('users')
