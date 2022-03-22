#!/usr/bin/env python3
import uvicorn

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
    msg: str


@app.post("/action1")
async def action1(request: Action1Request) -> Action1Response:
    print(f"doing action: `{request.msg}`")
    return Action1Response(msg=request.msg.replace("!", "?"))


@app.get("/tirepressure")
async def tirepressure(tire_number: int) -> dict:
    return {"hello": "world"}


app.mount("/", StaticFiles(directory="build"), name="ui")


if __name__ == "__main__":
    #kick off alarm thread here
    uvicorn.run(app, host="0.0.0.0", port=8000)