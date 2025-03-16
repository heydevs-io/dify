#------------------------------------------------------------------------------
# CODELIGHT_CUSTOMIZATION: Merge migration to resolve multiple heads
# Version: 1.0.0
# Author: Codelight - Lau Truong
# Date: 2025-03-16
#
# Description: This migration merges multiple head revisions that were created
# from parallel development branches. It resolves the "multiple heads" error
# by creating a convergence point in the migration history, allowing future
# migrations to proceed from a single head. This ensures database schema
# consistency across all environments and prevents migration conflicts during
# deployment.
#------------------------------------------------------------------------------

"""empty message
Revision ID: b4ea246ec0bf
Revises: 35ac98f57e80, f051706725cc
Create Date: 2025-03-16 14:36:12.463389

"""
from alembic import op
import models as models
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4ea246ec0bf'
down_revision = ('35ac98f57e80', 'f051706725cc')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
