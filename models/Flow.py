from database.database import Base, Session, engine
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Integer, String, ForeignKey, Enum
from typing import List, Optional
import enum
from pydantic import BaseModel

class STATE_TYPE(enum.Enum):
    START = 1
    NORMAL = 2
    END = 3

class Flow(Base):
    __tablename__ = 'flow'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    desc: Mapped[str] = mapped_column(String)

    state: Mapped[Optional[List['State']]] = relationship(back_populates='flow')

    def __str__(self):
        return f"Flow({self.id}, {self.name})"
    
class FlowSchema(BaseModel):
    name: str
    desc: str
    
    
class State(Base):
    __tablename__ = 'state'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    desc: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(Enum(STATE_TYPE))

    flow_id: Mapped[int] = mapped_column(ForeignKey('flow.id', ondelete='CASCADE'))
    flow: Mapped[Flow] = relationship(back_populates='state')

    prev_state_id: Mapped[Optional[Integer]] = mapped_column(Integer, ForeignKey('state.id'), nullable=True)
    prev_state: Mapped['State'] = relationship('State')

    def __str__(self):
        return f"State({self.id}, {self.name})"
    
class StateSchema(BaseModel):
    name: str
    desc: str
    type: STATE_TYPE
    flow_id: int
    prev_state_id: int | None = None