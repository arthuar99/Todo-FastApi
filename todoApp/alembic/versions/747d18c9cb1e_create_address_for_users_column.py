"""Create address for users column

Revision ID: 747d18c9cb1e
Revises: 
Create Date: 2025-08-20 17:27:05.786657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '747d18c9cb1e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users' , sa.Column ('phone_number' , sa.String , nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    
