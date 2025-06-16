"""Add ban columns to users table

Revision ID: 1234567890ab
Revises: previous_migration_id
Create Date: 2025-06-15 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns for ban functionality
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=True, server_default='0', comment='Indica si el usuario está baneado'))
    op.add_column('users', sa.Column('ban_reason', sa.String(255), nullable=True, comment='Razón de la restricción'))
    op.add_column('users', sa.Column('ban_expires_at', sa.DateTime(), nullable=True, comment='Fecha de expiración de la restricción'))
    op.add_column('users', sa.Column('banned_at', sa.DateTime(), nullable=True, comment='Fecha en que se aplicó la restricción'))
    op.add_column('users', sa.Column('banned_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, comment='ID del administrador que aplicó la restricción'))
    op.add_column('users', sa.Column('suspension_type', sa.Enum('none', 'temporary', 'permanent', name='suspension_type_enum'), server_default='none', nullable=False, comment='Tipo de suspensión'))
    op.add_column('users', sa.Column('suspension_until', sa.DateTime(), nullable=True, comment='Hasta cuándo está suspendido el usuario'))
    
    # Create index for better performance on ban-related queries
    op.create_index('idx_user_ban_status', 'users', ['is_banned', 'suspension_type', 'ban_expires_at', 'suspension_until'])
    
    # Set default values for existing users
    op.execute("UPDATE users SET is_banned = FALSE WHERE is_banned IS NULL")
    op.execute("UPDATE users SET suspension_type = 'none' WHERE suspension_type IS NULL")
    
    # Make is_banned non-nullable after setting defaults
    op.alter_column('users', 'is_banned', existing_type=sa.BOOLEAN(), nullable=False)

def downgrade():
    # Drop the index first
    op.drop_index('idx_user_ban_status', 'users')
    
    # Drop the columns in reverse order to avoid dependency issues
    op.drop_column('users', 'suspension_until')
    op.drop_column('users', 'suspension_type')
    op.drop_column('users', 'banned_by')
    op.drop_column('users', 'banned_at')
    op.drop_column('users', 'ban_expires_at')
    op.drop_column('users', 'ban_reason')
    op.drop_column('users', 'is_banned')
    
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS suspension_type_enum")
