#!/usr/bin/env python3
import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
alarm = Alarm()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index():
    return RedirectResponse(url="/index.html")


class Action1Request(BaseModel):
    msg: str


class Action1Response(BaseModel):
    state: json


@app.post("/alarm_state")
async def alarm_state(request: Action1Request) -> Action1Response:
    return Action1Response(state=alarm.json())


@app.get("/tirepressure")
async def tirepressure(tire_number: int) -> dict:
    return {"hello": "world"}


app.mount("/", StaticFiles(directory="build"), name="ui")



if __name__ == "__main__":
    alarm.run_thread()
    uvicorn.run(app, host="0.0.0.0", port=8000)