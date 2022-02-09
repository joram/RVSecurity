#!/usr/bin/env python3
import uvicorn

from fastapi import FastAPI
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

app = FastAPI()


@app.get("/")
async def index():
    return RedirectResponse(url="/index.html")


@app.get("/tirepressure")
async def tirepressure(tire_number: int) -> dict:
    return {"hello": "world"}


app.mount("/", StaticFiles(directory="build"), name="ui")
