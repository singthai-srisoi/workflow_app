from database.database import Base, Session, engine
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Integer, String, ForeignKey, Enum
from typing import List, Optional
import enum
from pydantic import BaseModel

from .Flow import Flow, State, STATE_TYPE

class ACTION(enum.Enum):
    START       = 0     # start flow
    NEXT        = 1     # next state
    PREVIOUS    = 2     # previous state
    JUMP        = 3     # jump to state
    TERMINATE   = 4     # end the flow
    RESTART     = 5     # restart flow
    CANCEL      = 6     # cancel flow


class Request(Base):
    __tablename__ = 'request'

    id: Mapped[int] = mapped_column(primary_key=True)
    remark: Mapped[str] = mapped_column(String)
    last_action: Mapped[Optional[str]] = mapped_column(Enum(ACTION), nullable=True)

    flow_id: Mapped[int] = mapped_column(ForeignKey('flow.id', ondelete='CASCADE'))
    flow: Mapped[Flow] = relationship('Flow')

    current_state_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('state.id'), nullable=True)
    current_state: Mapped[State] = relationship('State')

    request_action: Mapped[Optional[List['RequestAction']]] = relationship(back_populates='request')

    def __str__(self):
        return f"Request({self.id}, {self.remark})"
    
class RequestSchema(BaseModel):
    remark: str
    last_action: ACTION | None = None
    flow_id: int
    current_state_id: int | None = None

class RequestAction(Base):
    __tablename__ = 'request_action'

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(Enum(ACTION))
    comment: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    request_id: Mapped[int] = mapped_column(ForeignKey('request.id', ondelete='CASCADE'))
    request: Mapped[Request] = relationship(back_populates='request_action')

    # state_id: Mapped[int] = mapped_column(ForeignKey('state.id', ondelete='CASCADE'))
    # state: Mapped[State] = relationship('State')

    def __str__(self):
        return f"RequestAction({self.id}, {self.action})"
    
class RequestActionSchema(BaseModel):
    action: ACTION
    request_id: int
    comment: str | None
    state_id: int | None    # state_id is required for JUMP action

