"""Añade logica de roles y funcionario_id a Apoyo

Revision ID: 1b3e49bd616b
Revises: 411bc66fffcf
Create Date: 2025-10-29 22:11:49.363080

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1b3e49bd616b'
down_revision = '411bc66fffcf'
branch_labels = None
depends_on = None


def upgrade():
    # ### SOLO EJECUTAMOS LOS CAMBIOS PARA 'apoyos' ###
    with op.batch_alter_table('apoyos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('funcionario_id', sa.Integer(), nullable=True))
        batch_op.alter_column('usuario_id',
               existing_type=sa.INTEGER(),
               nullable=True) # <-- Cambio clave de nullable=False a nullable=True
        batch_op.create_unique_constraint('uq_funcionario_reporte', ['funcionario_id', 'reporte_id'])
        batch_op.create_foreign_key('fk_apoyos_funcionario_id', 'funcionarios', ['funcionario_id'], ['id']) # Nombre explícito de FK
    # ### FIN DE CAMBIOS ###


def downgrade():
    # ### SOLO REVERTIMOS LOS CAMBIOS PARA 'apoyos' ###
    with op.batch_alter_table('apoyos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_apoyos_funcionario_id', type_='foreignkey')
        batch_op.drop_constraint('uq_funcionario_reporte', type_='unique')
        batch_op.alter_column('usuario_id',
               existing_type=sa.INTEGER(),
               nullable=False) # Revertir a nullable=False
        batch_op.drop_column('funcionario_id')
    # ### FIN DE CAMBIOS ###