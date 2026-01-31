"""Initial database schema migration.

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-31 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create role enum
    op.execute("CREATE TYPE roleenum AS ENUM ('admin', 'user')")
    
    # Create action enum
    op.execute("CREATE TYPE actionenum AS ENUM ('login', 'face_scan', 'download')")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'user', name='roleenum'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for users
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_created_at', 'users', ['created_at'])
    
    # Create photos table
    op.create_table(
        'photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('drive_file_id', sa.String(), nullable=False),
        sa.Column('drive_url', sa.String(), nullable=False),
        sa.Column('day_name', sa.String(), nullable=False),
        sa.Column('face_embedding', postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('drive_file_id')
    )
    
    # Create indexes for photos
    op.create_index('ix_photos_drive_file_id', 'photos', ['drive_file_id'])
    op.create_index('ix_photos_day_name', 'photos', ['day_name'])
    op.create_index('ix_photos_indexed_at', 'photos', ['indexed_at'])
    
    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', postgresql.ENUM('login', 'face_scan', 'download', name='actionenum'), nullable=False),
        sa.Column('photo_count', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for activity_logs
    op.create_index('ix_activity_logs_user_id', 'activity_logs', ['user_id'])
    op.create_index('ix_activity_logs_action', 'activity_logs', ['action'])
    op.create_index('ix_activity_logs_timestamp', 'activity_logs', ['timestamp'])


def downgrade() -> None:
    """Drop all tables and types."""
    # Drop tables
    op.drop_index('ix_activity_logs_timestamp', table_name='activity_logs')
    op.drop_index('ix_activity_logs_action', table_name='activity_logs')
    op.drop_index('ix_activity_logs_user_id', table_name='activity_logs')
    op.drop_table('activity_logs')
    
    op.drop_index('ix_photos_indexed_at', table_name='photos')
    op.drop_index('ix_photos_day_name', table_name='photos')
    op.drop_index('ix_photos_drive_file_id', table_name='photos')
    op.drop_table('photos')
    
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE actionenum")
    op.execute("DROP TYPE roleenum")
