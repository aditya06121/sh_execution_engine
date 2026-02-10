"""
Purpose:
Owns job state transitions.
This file is the heart of the execution engine.
What goes here
Infinite loop
Pull job from queue
Update job state
Call executor
Capture result
Emit logs / store result
What must NOT go here
HTTP
Dockerfile details
API schema definitions
"""