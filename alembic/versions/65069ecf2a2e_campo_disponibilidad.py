"""campo disponibilidad

Revision ID: 65069ecf2a2e
Revises: 287cf728e31e
Create Date: 2026-06-29 12:24:26.347651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65069ecf2a2e'
down_revision: Union[str, Sequence[str], None] = '287cf728e31e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE estadochofer AS ENUM ('DESCONECTADO', 'DISPONIBLE', 'EN_VIAJE')")
    op.add_column('choferes', sa.Column('estado_chofer', sa.Enum('DESCONECTADO', 'DISPONIBLE', 'EN_VIAJE', name='estadochofer'), nullable=True))


def downgrade() -> None:
    # 1. Eliminar la columna
    op.drop_column('choferes', 'estado_chofer')
    op.execute("DROP TYPE estadochofer")
