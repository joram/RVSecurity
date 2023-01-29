#!/usr/bin/env python3
import uvicorn
#import alarm

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import random
import math

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


class DataResponse(BaseModel):
    var1: float
    var2: float
    var3: float
    var4: float
    var5: float
    var6: float
    var7: float
    var8: float
    var9: float
    var10: float
    var11: float
    var12: float


@app.get("/data")
async def data() -> DataResponse:

    # TODO: get real data
    return DataResponse(
        var1=round(random.random(), 2),
        var2=round(random.random(), 2),
        var3=round(random.random(), 2),
        var4=round(random.random(), 2),
        var5=round(random.random(), 2),
        var6=round(random.random(), 2),
        var7=round(random.random(), 2),
        var8=round(random.random(), 2),
        var9=round(random.random(), 2),
        var10=round(random.random(), 2),
        var11=round(random.random(), 2),
        var12=round(random.random(), 2),
    )

@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}


app.mount("/", StaticFiles(directory="build"), name="ui")


if __name__ == "__main__":
    #kick off alarm thread here

    # "0.0.0.0" => accept requests from any IP addr
    #uvicorn.run("app", host="0.0.0.0", port=80, reload=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)