from fastapi import FastAPI, Request, Response, status
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware  # Import CORS middleware
from core.config import settings
import os
import httpx
import re
import logging
import json
import time

from ldap3 import Connection, Server

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

log = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates", trim_blocks=True, lstrip_blocks=True)

app = FastAPI(title="FE", version="3.0.0")

origins = [
    "http://127.0.0.1:8000",  # EXACTLY your frontend's origin
    "http://localhost:8000",  # If you are running your frontend with localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # If needed
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    print(f"{settings.IBKR_BASE}portfolio/{settings.PARTNER_ACC}/summary")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}portfolio/{settings.PARTNER_ACC}/summary"  # Construct the target URL
            response = await client.get(target_url)
            acc_data = response.json()

        return templates.TemplateResponse("home/new.html", {"acc_data": acc_data, "request": request})

    except Exception as e:
        raise Exception()


@app.get("/screener-stocks")
async def screener_stocks():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.BE_BASE}screener-stocks-be"  # Construct the target URL
            print(target_url)
            response = await client.get(target_url)
            return response.json()
    except Exception as e:
        raise Exception()


@app.get("/screener", response_class=HTMLResponse)
async def home(request: Request):
    try:

        return templates.TemplateResponse("home/screener_page.html", {"request": request})

    except Exception as e:
        raise Exception()


@app.get("/cash-info")
async def cash_info():
    """
    This endpoint forwards requests to the actual backend API,
    avoiding CORS issues by making the request from the same origin.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}portfolio/{settings.PARTNER_ACC}/summary"  # Construct the target URL
            response = await client.get(target_url)
            return response.json()

    except Exception as e:
        raise Exception()


@app.get("/positions")
async def positions():
    """
    This endpoint forwards requests to the actual backend API,
    avoiding CORS issues by making the request from the same origin.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}portfolio/{settings.PARTNER_ACC}/positions/0"  # Construct the target URL
            response = await client.get(target_url)
            js_res = response.json()
            res = []
            for i in js_res:
                if i["position"] != 0:
                    res.append(i)
            return res

    except Exception as e:
        raise Exception()


@app.get("/acc-info")
async def acc_info():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}portfolio/DUH196417/positions/0"  # Construct the target URL
            response = await client.get(target_url)
            return response.json()
    except Exception as e:
        raise Exception()


@app.get("/manage", response_class=HTMLResponse)
async def manage(request: Request):
    return templates.TemplateResponse("home/manage_symbol.html", {"request": request})


@app.get("/get-active-orders/{conid}")
async def get_active_orders(conid: int, request: Request):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}iserver/account/orders"  # Construct the target URL
            response = await client.get(target_url)
            res = response.json()

    except Exception as e:
        raise e


@app.get("/get-all-active-orders")
async def get_all_active_orders():
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}iserver/account/orders"
            response = await client.get(target_url)
            data = response.json()["orders"]

            # print("API Response:", data)  # Debugging output

            return data  # Returning response as is

    except Exception as e:
        raise Exception(f"Error: {e}")


async def cancel_order(order_id):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            target_url = f"{settings.IBKR_BASE}iserver/account/{settings.PARTNER_ACC}/order/{order_id}"  # Construct the target URL
            response = await client.delete(target_url)
            return response.json()
    except Exception as e:
        raise Exception()


async def send_market_order(con_id, side, quantity):
    """Submits a market order to force close a position."""
    mrk_ord = f"{datetime.now().timestamp()}_MRK_FORCE_CLOSE"
    json_body = {
        "orders": [
            {
                "cOID": mrk_ord,
                "conid": int(con_id),
                "orderType": "MKT",
                "side": side,
                "tif": "DAY",
                "quantity": quantity
            }
        ]
    }

    target_url = f"{settings.IBKR_BASE}iserver/account/{settings.PARTNER_ACC}/orders"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(target_url, json=json_body)  # Added URL and JSON body
            response.raise_for_status()  # Raise error if response is not 2xx
            print(response.json())
            return response.json()
    except httpx.HTTPStatusError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None


@app.post("/close-position")
async def close_pos(request: Request):
    """Closes all open positions for a given ticker."""
    try:
        data = await request.json()
        ticker = data["ticker"]
        print("############################################################################################")
        print(data)
        # Get all active orders
        supr = await suppress()
        orders = await get_all_active_orders()
        total_quantity = abs(data["qty"])
        opposite_side = "SELL" if data["qty"] > 0 else "BUY"
        conId = data["con_id"]
        if orders:
            for order in orders:
                if order["ticker"] == ticker and (
                        order['status'] == 'PreSubmitted' or order['status'] == "PendingSubmit" or order['status'] == "Submitted"):
                    await cancel_order(order["orderId"])
            await send_market_order(conId, opposite_side, total_quantity)
        else:
            await send_market_order(conId, opposite_side, total_quantity)

        return {"message": f"Closed position for {ticker}, sent {opposite_side} market order for {total_quantity} shares."}

    except Exception as e:
        raise Exception(f"Error: {e}")


@app.get("/get-all-trades")
async def get_all_trades():
    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                target_url = f"{settings.IBKR_BASE}iserver/account/trades?days=100"
                response = await client.get(target_url)
                data = response.json()

                # print("API Response:", data)  # Debugging output

                return data  # Returning response as is

        except Exception as e:
            raise Exception(f"Error: {e}")


async def suppress():
    start_time = time.time()
    timeout = 5
    json_body = {
        "messageIds": ["o163", "o354", "o383", "o451", "o10331"]
    }
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                target_url = f"{settings.IBKR_BASE}iserver/questions/suppress"
                response = await client.post(target_url, json=json_body)
                data = response.json()
                print("API Response:", data)  # Debugging output

                return data  # Returning response as is

        except Exception as e:
            raise Exception(f"Error: {e}")


@app.get("/orders", response_class=HTMLResponse)
async def orders(request: Request):
    return templates.TemplateResponse("home/order.html", {"request": request})


@app.post("/manage-pos")
async def manege_pos():
    pass
