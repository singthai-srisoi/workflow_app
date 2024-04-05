# Simple Workflow App

This is a simple workflow backend build using fastapi. The system allow user to:
> setup a workflow
> create a workflow request
> perform action on the request

To run this app, clone this repo and run
```cmd
pip install -r requirements.txt
uvicorn main:app --reload
```

***
## about the actions
System allowed user to perform some action on the request flow, those action include:
```python
class ACTION(enum.Enum):
    START       = 0     # start flow
    NEXT        = 1     # next state
    PREVIOUS    = 2     # previous state
    JUMP        = 3     # jump to state
    TERMINATE   = 4     # end the flow
    RESTART     = 5     # restart flow
    CANCEL      = 6     # cancel flow
```
