"""add_logs_to_jobs

Revision ID: f23456789abc
Revises: 722241e9f868
Create Date: 2026-05-01 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f23456789abc'
down_revision: Union[str, None] = '722241e9f868'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the 'logs' column to 'jobs' table
    op.add_column('jobs', sa.Column('logs', sa.Text(), nullable=True, server_default=''))


def downgrade() -> None:
    # Remove the 'logs' column from 'jobs' table
    op.drop_column('jobs', 'logs')
