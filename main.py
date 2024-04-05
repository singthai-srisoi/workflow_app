from fastapi import FastAPI, Query, Path, UploadFile
from pydantic import BaseModel
from typing import List, Annotated, Optional

from sqlalchemy import insert, select, update
from database.database import Base, Session, engine
from models.Flow import *
from models.Request import *

from pydantic import BaseModel

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/migrate/")
async def migrate():
    try: 
        await Base.metadata.create_all(bind=engine)
    except Exception as e:
        return {"message": str(e)}
    
    return {"message": "migrate success"}


# ================== FLOW SETTING ==================

@app.post("/flow/", tags=["flow"])
async def create_flow(flow: FlowSchema):
    flow = dict(flow)
    obj = Flow(**flow)

    # check if flow already exists
    if exist := Session.query(Flow).filter(Flow.name == obj.name).first():
        return {"message": "flow already exists", "data": exist.__dict__}

    Session.add(obj)
    data = obj.__dict__.copy()
    Session.commit()

    return {"message": "create flow success", "data": data}

@app.get("/flow/", tags=["flow"])
async def get_flows():
    flows = await Session.query(Flow).all()
    return {"message": "get flows success", "data": [flow.__dict__ for flow in flows]}

@app.get("/flow/{flow_id}", tags=["flow"])
async def get_flow(flow_id: int = Path(...)):
    flow = await Session.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        return {"message": "flow not found"}

    return {"message": "get flow success", "data": flow.__dict__}

@app.delete("/flow/{flow_id}", tags=["flow"])
async def delete_flow(flow_id: int = Path(...)):
    flow = Session.query(Flow).filter(Flow.id == flow_id).first()
    if not flow:
        return {"message": "flow not found"}

    Session.delete(flow)
    Session.commit()

    return {"message": "delete flow success"}

@app.post("/state/", tags=["flow"])
async def create_state(state: List[StateSchema]):
    # print(state)
    state = [dict(s) for s in list(state)]
    
    result = Session.scalars(
        insert(State).returning(State),
        state
    )
    Session.commit()

    # result to dict
    result = [r.__dict__ for r in result.all()]

    return {"message": "create state success", "data": result}

@app.get("/flow/state/{flow_id}", tags=["flow"])
async def get_states(flow_id: int = Path(...)):
    states = Session.query(State).filter(State.flow_id == flow_id).all()
    return {"message": "get states success", "data": [state.__dict__ for state in states]}



# ================== REQUEST SETTING ==================

@app.post("/request/", tags=["request"])
async def create_request(request: RequestSchema):
    request = dict(request)
    
    state = (
        Session.query(State)
        .filter(State.flow_id == request['flow_id'])
        .filter(State.type == STATE_TYPE.START)
        .first()
    )
    if not state:
        return {"message": "flow not found"}
    
    request['current_state_id'] = state.id

    obj = Request(**request)
    Session.add(obj)
    Session.flush()
    data = obj.__dict__.copy()

    req_action = {
        'action': ACTION.START,
        'request_id': obj.id
    }
    obj_action = RequestAction(**req_action)
    Session.add(obj_action)
    Session.commit()


    return {"message": "create request success", "data": data}

@app.get("/request/{request_id}", tags=["request"])
async def get_request(request_id: int = Path(...)):
    request = Session.query(Request).filter(Request.id == request_id).first()
    data = request.__dict__.copy()

    req_action = request.request_action
    data['request_action'] = [action.__dict__ for action in req_action]

    if not request:
        return {"message": "request not found"}

    return {"message": "get request success", "data": data}

@app.post("/request/action/", tags=["request"])
async def create_request_action(action: RequestActionSchema):
    action = dict(action)
    state_id = action.pop('state_id', None)
    req = Session.query(Request).filter(Request.id == action['request_id']).first()
    if not req:
        return {"message": "request not found"}
    
    if action['action'] == ACTION.NEXT:
        next_state = (
            Session.query(State)
            .filter(State.prev_state_id == req.current_state_id)
            .first()
        )
        if not next_state:
            return {"message": "next state not found"}
        elif req.current_state.type == STATE_TYPE.END:
            return {"message": "flow already completed"}
        elif req.last_action == ACTION.CANCEL:
            return {"message": "flow already cancelled"}
        
        req.current_state_id = next_state.id
        req.last_action = ACTION.NEXT
        # update request
        Session.add(req)
        Session.commit()
    elif action['action'] == ACTION.PREVIOUS:
        prev_state = (
            Session.query(State)
            .filter(State.id == req.current_state.prev_state_id)
            .first()
        )
        if not prev_state:
            return {"message": "previous state not found"}
        elif req.current_state.type == STATE_TYPE.START:
            return {"message": "flow already started"}
        elif req.last_action == ACTION.CANCEL:
            return {"message": "flow already cancelled"}
        
        req.current_state_id = prev_state.id
        req.last_action = ACTION.PREVIOUS
        # update request
        Session.add(req)
        Session.commit()
    elif action['action'] == ACTION.TERMINATE:
        last_state = (
            Session.query(State)
            .filter(State.flow_id == req.flow_id)
            .filter(State.type == STATE_TYPE.END)
            .first()
        )
        if not last_state:
            return {"message": "last state not found"}
        elif req.last_action == ACTION.CANCEL:
            return {"message": "flow already cancelled"}
        
        req.current_state_id = last_state.id
        req.last_action = ACTION.TERMINATE
        # update request
        Session.add(req)
        Session.commit()
    elif action['action'] == ACTION.RESTART:
        start_state = (
            Session.query(State)
            .filter(State.flow_id == req.flow_id)
            .filter(State.type == STATE_TYPE.START)
            .first()
        )
        if not start_state:
            return {"message": "start state not found"}
        
        stmt = (
            update(Request)
            .where(Request.id == req.id)
            .values(last_action=ACTION.RESTART)
            .values(current_state_id=start_state.id)
        )

        Session.execute(stmt)
        Session.commit()
    elif action['action'] == ACTION.CANCEL:
        req.last_action = ACTION.CANCEL
        # update request
        Session.add(req)
        Session.commit()
    elif action['action'] == ACTION.JUMP:
        if not state_id:
            return {"message": "state_id is required for JUMP action"}
        
        jump_state = (
            Session.query(State)
            .filter(State.id == state_id)
            .first()
        )
        if not jump_state:
            return {"message": "jump state not found"}
        
        req.current_state_id = jump_state.id
        req.last_action = ACTION.JUMP
        # update request
        Session.add(req)
        Session.commit()     
    else:
        return {"message": "action not found"}

    obj = RequestAction(**action)

    Session.add(obj)
    data = obj.__dict__.copy()
    Session.commit()

    return {"message": "create request action success", "data": data}

@app.get("/dummy/")
async def dummy():
    
    return  [
                {
                    "name": "start",
                    "desc": "start",
                    "type": STATE_TYPE.START,
                    "flow_id": 1,
                    "prev_state_id": None
                },
                {
                    "name": "in progress",
                    "desc": "waiting for approval",
                    "type": STATE_TYPE.NORMAL,
                    "flow_id": 1,
                    "prev_state_id": 1
                },
                {
                    "name": "complete",
                    "desc": "completed flow",
                    "type": STATE_TYPE.END,
                    "flow_id": 1,
                    "prev_state_id": 2
                }
            ]
