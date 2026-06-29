from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Body 
import subprocess
import threading
import struct
import socket
import time
import csv
import re
import os
import sys


csv_read_offset = 0


def resource_path(rel_path):
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, rel_path)
BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
current_csv_file = None
csv_lock = threading.Lock()

app = FastAPI()
app.mount("/static", StaticFiles(directory=resource_path("static")), name="static")
templates = Jinja2Templates(directory=resource_path("templates"))
LAST_IP_FILE = os.path.join(os.getcwd(), "last_ip.txt")

# ===================================== PLC Connection =============================================
PLC_PORT = 502
slave_id = 1
client = None
plc_connected = False
plc_ip = None
def connect_plc(ip: str):
    global client, plc_connected, plc_ip

    try:
        if client:
            client.close()

        client = ModbusTcpClient(ip, port=PLC_PORT, timeout=2)
        plc_connected = client.connect()
        plc_ip = ip if plc_connected else None

        if plc_connected:
            save_last_ip(ip)
            with lock:
                for k in latest_data:
                    latest_data[k] = 0
                for k in latest_data_1:
                    latest_data_1[k] = 0

        print(f"PLC connect {ip}: {plc_connected}")
        return plc_connected

    except Exception as e:
        plc_connected = False
        plc_ip = None
        print("PLC CONNECT ERROR:", e)
        return False
def mark_plc_disconnected():
    global plc_connected
    plc_connected = False
def plc_reconnect_task():
    while True:
        if plc_ip and not plc_connected:
            print("PLC offline → reconnecting...")
            connect_plc(plc_ip)
        time.sleep(2)


threading.Thread(target=plc_reconnect_task, daemon=True).start()
found_ips = []

def get_arp_ips():
    try:
        output = subprocess.check_output("arp -a", shell=True).decode(errors="ignore")
        ips = re.findall(r"(\d+\.\d+\.\d+\.\d+)", output)
        return list(set(ip for ip in ips if ip.startswith("192.168.")))
    except:
        return []

def scan_ips_task():
    global found_ips
    while True:
        found_ips = get_arp_ips()
        time.sleep(5)

# threading.Thread(target=scan_ips_task, daemon=True).start()

# LAST_IP_FILE = "last_ip.txt"


lock = threading.Lock()
stop_thread = False
current_page = "burst_auto"
current_page_1 = "burst_auto"   

read_address = {
    # /burst_auto
    "pressure_set"       : 40051,
    "pressure_actual"    : 40007,
    "rate_set1"          : 40053,
    "time_set"           : 40055,   
    "time_actual"        : 40165,
    "peak_actual"        : 40157,
    # "leak_set"           : 400,
    # "leak_actual"        : 4211,
    "MSG_b"              : 40032, 

    # /impluse_1_auto
    "press_max_set1"     : 40189,
    "press_max_actual1"  : 40007,
    "rate_max_set"       : 40078,
    "rate_max_actual"    : 40222,
    "dwell_max_set"      : 40080,
    "dwell_max_actual"   : 40228,
    "press_min_set"      : 40191,
    "rate_min_set"       : 40084,
    "rate_min_actual"    : 40224,
    "dwell_min_set"      : 40086,
    "dwell_min_actual"   : 40214,
    "cycles_set1"        : 40091,
    "cycles_actual_i1"   : 40217,
    "duration_set"       : 40095,     
    "duration_actual1"   : 40237,
    # "leak_set1"          : 4380,
    # "leak_actual1"       : 4249,  
    "MSG_i1"             : 40034,
    # "rate_max_actual_v"  : 40222,  
    # "dwell_max_actual_v" : 40228,    
    # "rate_min_actual_v"  : 40224,    
    # "dwell_min_actual_v" : 40214,  

    # /Stage_auto
    "stage_pressure"     : 40261,    
    "stage_count_set"    : 40252,
    "stage_count_actual" : 40284,
    "press_set"          : 40261,
    "press_actual"       : 40007,
    "rate_set2"          : 40264,
    "rate_actual"        : 40286,   
    "dwell_set"          : 40266,
    "dwell_actual"       : 40288, 
    "cycles_set"         : 40273,
    "cycles_actual"      : 40289,      
    "duration_set1"      : 40383,    
    "duration_actual"    : 40281,     
    "MSG_s"              : 40036,  

    # /manual
    "manual_press_limit" : 40001,   
    "manual_press_actual": 40007, 
    "press_actual_3"     : 40007,

    # /burst_edit
    "pressure_set_e"     : 40051, 
    "rate_set_e"         : 40053,  
    # "leak_set_e"         : 4300,    
    "duration_set_e"     : 40055,  

    # /impluse_1_edit
    "imp1_max_press"     : 40189,   
    "imp1_max_rate"      : 40078,     
    "imp1_max_dwell"     : 40080,     
    "imp1_min_press"     : 40191, 
    "imp1_min_rate"      : 40084,   
    "imp1_min_dwell"     : 40086,    
    "imp1_cycles"        : 40091,     
    "imp1_duration"      : 40095,     
    # "imp1_leak"          : 4380,
       
    # STAGE EDIT 
    "stage_count_set_a": 40252,
    "press_set_a":       40253,
    "stage_p1":          40301,
    "stage_r1":          40304,
    "stage_d1":          40306,
    "stage_p2":          40307,
    "stage_r2":          40310,
    "stage_d2":          40312,
    "stage_p3":          40313,
    "stage_r3":          40316,
    "stage_d3":          40318,
    "stage_p4":          40319,
    "stage_r4":          40322,
    "stage_d4":          40324,
    "stage_p5":          40325,
    "stage_r5":          40328,
    "stage_d5":          40330,
    "stage_p6":          40331,
    "stage_r6":          40334,
    "stage_d6":          40336,
    "stage_p7":          40337,
    "stage_r7":          40340,
    "stage_d7":          40342,
    "stage_p8":          40343,
    "stage_r8":          40346,
    "stage_d8":          40348,
    "stage_cycles":      40273,
    "stage_duration":    40383,
   # "stage_leak":       40360,         
}

control_regs = {
    # burst_auto
    "burst_start": 40037,
    "burst_stop":  40039,
    "burst_pause": 40041,


    # impluse_1_auto
    "i1_start": 40043,
    "i1_stop":  40045,
    "i1_pause": 40047,

    # stage_auto
    "stage_start": 40017,
    "stage_stop":  40019,
    "stage_pause": 40021,
}


latest_data = {k: 0 for k in read_address.keys()}
latest_data_1 = {k: 0 for k in read_address.keys()}
lock = threading.Lock()
stop_thread = False
float_registers = {
    # Manual
    "manual_press_limit",
    "manual_press_actual",

    # Burst auto
    "pressure_set",
    "pressure_actual",
    "rate_set1",
    "time_set",
    "time_actual",
    "peak_actual",

    # burst_edit
    "pressure_set_e", 
    "rate_set_e",
    "duration_set_e" ,

    # Impulse auto
    "press_max_set1",
    "press_max_actual1",
    "press_min_set",
    

    # impulse edit
    "imp1_min_press",      
    "imp1_max_press",

    # Stage auto
    "stage_pressure",
    "press_set",
    "press_actual",

    # Edit / duration
    # "duration_set",
    # "duration_set1",
    "duration_set_e",
    # "stage_duration",

    # Stage edit 
    "stage_p1",
    "stage_p2",
    "stage_p3",
    "stage_p4",
    "stage_p5",
    "stage_p6",
    "stage_p7",
    "stage_p8",
    "press_set_a"
    
}

uint32_registers = {
    "cycles_set1",  
    "stage_duration",
    "cycles_set",
    "duration_set",
    "imp1_cycles",
    "cycles_actual_i1",
    "imp1_duration",
    "duration_actual1",
    "stage_cycles",
    "cycles_actual",
    "duration_set1",
    "duration_actual",
    
}

# Register groups for different pages
page_regs = {

    "burst_auto": [
        "pressure_set", "pressure_actual",
        "rate_set1", "time_set", "time_actual",
        "peak_actual",
        "MSG_b"
    ],

    "impluse_1_auto": [
        "press_max_set1", "press_max_actual1",
        "rate_max_set", "rate_max_actual",
        "dwell_max_set", "dwell_max_actual",
        "press_min_set", "rate_min_set",
        "rate_min_actual", "dwell_min_set",
        "dwell_min_actual", "cycles_set1",
        "cycles_actual_i1", "duration_set",
        "duration_actual1", "MSG_i1", 
    ],

    "stage_auto": [
        "stage_pressure", "stage_count_set",
        "stage_count_actual", "press_set",
        "press_actual", "rate_set2",
        "rate_actual", "dwell_set",
        "dwell_actual", "cycles_set",
        "duration_set1", "duration_actual",
        "MSG_s","cycles_actual",
    ],

    "manual": [
        "manual_press_limit", "manual_press_actual",
        "press_actual_3"
    ],

    "burst_edit": [
        "pressure_set_e", "rate_set_e",
        "duration_set_e"
    ],

    "impluse_1_edit": [
        "imp1_max_press", "imp1_max_rate",
        "imp1_max_dwell", "imp1_min_press",
        "imp1_min_rate", "imp1_min_dwell",
        "imp1_cycles", "imp1_duration",
    ],

    "stage_edit": [
        "press_set_a", "stage_count_set_a",
        "stage_p1", "stage_r1", "stage_d1",
        "stage_p2", "stage_r2", "stage_d2",
        "stage_p3", "stage_r3", "stage_d3",
        "stage_p4", "stage_r4", "stage_d4",
        "stage_p5", "stage_r5", "stage_d5",
        "stage_p6", "stage_r6", "stage_d6",
        "stage_p7", "stage_r7", "stage_d7",
        "stage_p8", "stage_r8", "stage_d8",
        "stage_cycles", "stage_duration"
    ]
}

page_regs_1 = {

    "burst_auto": [
        "pressure_actual", "time_actual", "peak_actual",
    ],

    "impluse_1_auto": [
        "press_max_actual1",
        "rate_min_actual",
        "dwell_min_actual",
        "rate_max_actual",
        "dwell_max_actual",
        "cycles_actual_i1",
        "duration_actual1",
    ],

    "stage_auto": [
        "press_actual",
        "stage_count_actual",
        "rate_actual",
        "dwell_actual",
        # "cycles_actual",
        "duration_actual",
    ]
}

scale_map = {

    # burst_auto
    "pressure_actual": 1,
    "rate_set1": 1,
    "time_actual": 1,
    "peak_actual": 1,

    # impluse_1_auto
    "press_max_actual1": 1,
    "rate_max_actual": 1,
    "dwell_max_actual": 1,
    "rate_min_actual": 1,
    "dwell_min_actual": 1,
    "cycles_actual_i1": 1,
    "duration_actual1": 1,

    # stage_auto
    "stage_count_actual" : 1,
    "press_actual": 1,
    "rate_actual": 1,
    "dwell_actual": 1,
    "cycles_actual": 1,
    "duration_actual" : 1,

}

def dynamic_scale(key, latest):
    return scale_map.get(key, 1)

class CSVManager:
    def __init__(self):
        self.active = False
        self.file = None
        self.thread = None

    def start(self, page):

        global current_page_1
        current_page_1 = page

        if self.active:
            return

        self.active = True
        filename = f"logs/{page}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        self.file = open(filename, "w")

        header = ["time"] + page_regs_1[page]
        self.file.write(",".join(header) + "\n")

        self.thread = threading.Thread(target=self.run, args=(page,), daemon=True)
        self.thread.start()

    def stop(self):
        self.active = False
        time.sleep(0.1)
        if self.file:
            self.file.close()
            self.file = None

    def run(self, page):
        while self.active:
            row = []

            for key in page_regs_1[page]:

                raw = latest_data_1.get(key)

                if raw is None:
                    scaled = 0.0
                else:
                    scale = dynamic_scale(key, latest_data_1) or 1
                    scaled = raw / scale

                row.append(f"{scaled:.2f}")

            if self.file:
                ts = time.strftime("%Y-%m-%d %H:%M:%S.") + f"{int((time.time()%1)*1000):03d}"
                self.file.write(ts + "," + ",".join(row) + "\n")

            time.sleep(0.05)

page_pressure_key = {
    "burst_auto": "pressure_actual",
    "impluse_1_auto": "press_max_actual1",
    "stage_auto": "press_actual"
}
def read_float_ascii(addr):
    """
    EXACT behavior as code 1:
    - holding registers
    - addr - 40001
    - MS word first
    - IEEE-754 big endian
    """
    try:
        with lock:
            res = client.read_holding_registers(addr - 40001, 2, unit=slave_id)

        if not res or res.isError():
            return None

        hi, lo = res.registers
        raw = (hi << 16) | lo
        return struct.unpack(">f", raw.to_bytes(4, "big"))[0]

    except Exception as e:
        print("FLOAT READ ERROR:", e)
        return None


def read_uint32_ascii(addr):
    """
    EXACT behavior as code 1 INT32 read:
    - holding registers
    - lo word first, hi word second
    - signed conversion
    """
    try:
        with lock:
            res = client.read_holding_registers(addr - 40001, 2, unit=slave_id)
        # print("RAW 40040–40043:", res.registers)

        if not res or res.isError():
            return None

        hi = res.registers[0]
        lo = res.registers[1]

        value = (hi << 16) | lo

        # signed conversion (same as code 1)
        if value & 0x80000000:
            value -= 0x100000000

        return value

    except Exception as e:
        print("INT32 READ ERROR:", e)
        return None
   
def read_plc_task():
    global current_page, latest_data
    import math
    import random
    sim_t = 0.0

    while not stop_thread:
        if not plc_connected or not client :
            with lock:
                keys = page_regs.get(current_page, [])
            sim_t += 0.2
            temp = {}
            for name in keys:
                # Setpoint Simulation
                if name in ["pressure_set", "press_set", "press_set_a", "pressure_set_e"]:
                    temp[name] = 6.0
                elif name in ["rate_set1", "rate_set2", "rate_set_e"]:
                    temp[name] = 1.5
                elif name in ["time_set", "duration_set", "duration_set1", "duration_set_e"]:
                    temp[name] = 30.0
                elif name in ["cycles_set", "cycles_set1", "stage_cycles"]:
                    temp[name] = 100
                elif name == "press_max_set1":
                    temp[name] = 7.0
                elif name == "press_min_set":
                    temp[name] = 2.0
                elif name == "dwell_max_set":
                    temp[name] = 5.0
                elif name == "dwell_min_set":
                    temp[name] = 5.0
                elif name == "stage_pressure":
                    temp[name] = 5.0
                elif name == "stage_count_set":
                    temp[name] = 8
                elif name == "manual_press_limit":
                    temp[name] = 10.0
                # Actual values simulation
                elif "pressure" in name or "press" in name:
                    temp[name] = (5.0 + math.sin(sim_t / 3.0) * 1.8 + random.uniform(-0.05, 0.05)) * 1
                elif "time" in name or "dwell" in name or "duration" in name:
                    temp[name] = round(sim_t % 30.0, 2) * 60  # scaled in client
                elif "cycles" in name or "count" in name:
                    temp[name] = int(sim_t / 5.0) % 10
                elif "rate" in name:
                    temp[name] = round(1.2 + random.uniform(-0.05, 0.05), 2)
                elif "peak" in name:
                    with lock:
                        temp[name] = max(latest_data.get("peak_actual", 0.0), temp.get("pressure_actual", 0.0))
                elif name in ["MSG_b", "MSG_i1", "MSG_s"]:
                    temp[name] = 1  # 1 = running
                else:
                    temp[name] = 0.0

            with lock:
                for k, v in temp.items():
                    latest_data[k] = v
            time.sleep(0.2)
            continue



        with lock:
            keys = page_regs.get(current_page, [])

        temp = {}

        for name in keys:
            reg = read_address[name]

            try:
                if name in float_registers:
                    value = read_float_ascii(reg)

                elif name in uint32_registers:
                    value = read_uint32_ascii(reg)

                else:
                    with lock:
                     res = client.read_holding_registers(reg-40001, 1, unit=slave_id)
                    value = res.registers[0] if res and hasattr(res, "registers") else None

                temp[name] = value

            except:
                temp[name] = None

            time.sleep(0.005)

        with lock:
            for k, v in temp.items():
                latest_data[k] = v

def h_read_plc_task():
    global current_page_1, latest_data_1
    import math
    import random
    sim_t = 0.0

    while not stop_thread:
        if not plc_connected or not client:
            with lock:
                keys = page_regs_1.get(current_page_1, [])
            sim_t += 0.2
            temp = {}
            for name in keys:
                if "pressure" in name or "press" in name:
                    temp[name] = (5.0 + math.sin(sim_t / 3.0) * 1.8 + random.uniform(-0.05, 0.05)) * 1
                elif "time" in name or "dwell" in name or "duration" in name:
                    temp[name] = round(sim_t % 30.0, 2) * 60
                elif "cycles" in name or "count" in name:
                    temp[name] = int(sim_t / 5.0) % 10
                elif "rate" in name:
                    temp[name] = round(1.2 + random.uniform(-0.05, 0.05), 2)
                elif "peak" in name:
                    with lock:
                        temp[name] = max(latest_data_1.get("peak_actual", 0.0), temp.get("pressure_actual", 0.0))
                else:
                    temp[name] = 0.0

            with lock:
                for k, v in temp.items():
                    latest_data_1[k] = v
            time.sleep(0.2)
            continue



        with lock:
            keys = page_regs_1.get(current_page_1, [])

        temp = {}

        for name in keys:
            reg = read_address[name]

            try:
                if name in float_registers:
                    value = read_float_ascii(reg)

                elif name in uint32_registers:
                    value = read_uint32_ascii(reg)

                else:
                    with lock:
                      res = client.read_holding_registers(reg-40001, 1, unit=slave_id)
                    value = res.registers[0] if res and hasattr(res, "registers") else None

                temp[name] = value

            except:
                temp[name] = None

        with lock:
            for k, v in temp.items():
                latest_data_1[k] = v

# Start background thread
t1 = threading.Thread(target=read_plc_task, daemon=True)
t1.start()

t2 = threading.Thread(target=h_read_plc_task, daemon=True)
t2.start()

# API Endpoints
@app.get("/plc_value")
async def plc_value():
    with lock:
        return latest_data
    
    
@app.get("/get_available_ips")
def get_available_ips():
    # Perform scan ONLY when endpoint is called
    ips = get_arp_ips()

    # Always include currently connected PLC
    if plc_ip:
        ips = list(set(ips + [plc_ip]))

    return {
        "ips": sorted(ips),
        "connected": plc_ip
    }


@app.get("/set_page/{p}")
def set_page(p: str):
    global current_page, current_page_1
    if p in page_regs:
        current_page = p
        current_page_1 = p 
    return {"active_page": current_page}
   
def load_last_ip():
    if os.path.exists(LAST_IP_FILE):
        try:
            with open(LAST_IP_FILE, "r") as f:
                return f.read().strip()
        except:
            pass
    return None

def save_last_ip(ip):
    try:
        with open(LAST_IP_FILE, "w") as f:
            f.write(ip)
    except:
        pass

# HTML Pages
@app.get("/", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse(request, "welcome.html", {"request": request})

# @app.get("/back", response_class=HTMLResponse)
# async def edit_program(request: Request):
#     return templates.TemplateResponse(request, "welcome.html", {"request": request})

@app.get("/main", response_class=HTMLResponse)
async def main_page(request: Request):
    return templates.TemplateResponse(request, "main.html", {"request": request})

@app.get("/auto", response_class=HTMLResponse)
async def auto_page(request: Request):
    return templates.TemplateResponse(request, "auto.html", {"request": request})

@app.get("/manual", response_class=HTMLResponse)
async def manual_page(request: Request):
    return templates.TemplateResponse(request, "manual.html", {"request": request})

@app.get("/edit_program", response_class=HTMLResponse)
async def edit_program(request: Request):
    return templates.TemplateResponse(request, "edit_program.html", {"request": request})

@app.get("/burst_auto", response_class=HTMLResponse)
async def burst_auto(request: Request):
    return templates.TemplateResponse(request, "burst_auto.html", {"request": request})

@app.get("/stage_auto", response_class=HTMLResponse)
async def stage_auto(request: Request):
    return templates.TemplateResponse(request, "stage_auto.html", {"request": request})

@app.get("/impluse_1_auto", response_class=HTMLResponse)
async def impluse_1_auto(request: Request):
    return templates.TemplateResponse(request, "impluse_1_auto.html", {"request": request})

@app.get("/burst_edit", response_class=HTMLResponse)
async def burst_edit(request: Request):
    return templates.TemplateResponse(request, "burst_edit.html", {"request": request})

@app.get("/stage_edit", response_class=HTMLResponse)
async def stage_edit(request: Request):
    return templates.TemplateResponse(request, "stage_edit.html", {"request": request})

@app.get("/impluse_1_edit", response_class=HTMLResponse)
async def impluse_1_edit(request: Request):
    return templates.TemplateResponse(request, "impluse_1_edit.html", {"request": request})

@app.get("/graph", response_class=HTMLResponse)
async def auto_page(request: Request):
    return templates.TemplateResponse(request, "graph.html", {"request": request})
# ==================== Coil Read and Write ===========================
def read_int32(addr):
    try:
        with lock:
            res = client.read_holding_registers(addr - 40001, 2, unit=slave_id)
        if not res or res.isError():
            return None

        lo = res.registers[1]
        hi = res.registers[0]
        return (hi << 16) | lo
    except:
        return None


def write_int32(addr, value):
    try:
        v = int(value) & 0xFFFFFFFF
        lo = v & 0xFFFF
        hi = (v >> 16) & 0xFFFF

        with lock:
            res = client.write_registers(addr - 40001, [hi, lo], unit=slave_id)

        return res and not res.isError()
    except:
        return False

# ============================ Indicator ====================================
def read_int32_siements(addr):
    try:
        with lock:
            res = client.read_holding_registers(addr - 40001, 2, unit=slave_id)

        if not res or res.isError():
            return None

        lo = res.registers[0]   # LOW word
        hi = res.registers[1]   # HIGH word

        value = (hi << 16) | lo

        # signed conversion (optional but safe)
        if value & 0x80000000:
            value -= 0x100000000

        return value
    except:
        return None
@app.get("/indicator_plc")
def indicator_plc():
    INDICATOR_REG = 40016   # <-- your real PLC register

    # PLC disconnected → force RED
    if not plc_connected or not client:
        return {
            "ok": False,
            "value": 0,
            "connected": False
        }

    val = read_int32_siements(INDICATOR_REG)

    if val is None:
        return {
            "ok": False,
            "value": 0,
            "connected": True
        }

    return {
        "ok": True,
        "value": 1 if val == 1 else 0,
        "connected": True
    }

# ============================ Burst Auto ====================================
@app.post("/burst_start")
def burst_start():
    ok = write_int32(control_regs["burst_start"], 1)
    return {"success": ok}

@app.post("/burst_stop")
def burst_stop():
    ok = write_int32(control_regs["burst_stop"], 1)
    return {"success": ok}

@app.post("/burst_pause")
def burst_pause():
    addr = control_regs["burst_pause"]
    cur = read_int32(addr) or 0
    new = 0 if cur else 1
    ok = write_int32(addr, new)
    return {"success": ok, "state": new}

@app.get("/burst_pause_state")
def burst_pause_state():
    return {"state": read_int32(control_regs["burst_pause"]) == 1}
# ============================= Impulse Auto ============================================
@app.post("/i1_start")
def i1_start():
    return {"success": write_int32(control_regs["i1_start"], 1)}

@app.post("/i1_stop")
def i1_stop():
    return {"success": write_int32(control_regs["i1_stop"], 1)}

@app.post("/i1_pause")
def i1_pause():
    addr = control_regs["i1_pause"]
    cur = read_int32(addr) or 0
    new = 0 if cur else 1
    return {"success": write_int32(addr, new), "state": new}

@app.get("/i1_pause_state")
def i1_pause_state():
    return {"state": read_int32(control_regs["i1_pause"]) == 1}
# =================================== Stage Auto =============================================
@app.post("/stage_start")
def stage_start():
    return {"success": write_int32(control_regs["stage_start"], 1)}

@app.post("/stage_stop")
def stage_stop():
    return {"success": write_int32(control_regs["stage_stop"], 1)}

@app.post("/stage_pause")
def stage_pause():
    addr = control_regs["stage_pause"]
    cur = read_int32(addr) or 0
    new = 0 if cur else 1
    return {"success": write_int32(addr, new), "state": new}

@app.get("/stage_pause_state")
def stage_pause_state():
    return {"state": read_int32(control_regs["stage_pause"]) == 1}
# ========================================================================================
# Write Endpoints


@app.post("/write_manual_limit")
async def write_manual_limit(data: dict = Body(...)):
    try:
        val = float(data.get("value"))
        addr = read_address["manual_press_limit"]

        ok = write_float_real(addr, val)
        return {"success": ok}

    except Exception as e:
        return {"success": False}

@app.post("/write_burst_value")
async def write_burst_value(data: dict = Body(...)):
    try:
        key = data.get("key")
        val = float(data.get("value", 0))

        if key not in read_address:
            return {"success": False}

        addr = read_address[key]

        if key in float_registers:
            builder = BinaryPayloadBuilder(byteorder=Endian.Big, wordorder=Endian.Big)
            builder.add_32bit_float(val)
            payload = builder.to_registers()
            with lock:
             res = client.write_registers(addr-40001, payload, unit=slave_id)
            return {"success": not res.isError()}
        with lock:
         res = client.write_register(addr-40001, int(val), unit=slave_id)
        return {"success": not res.isError()}

    except Exception as e:
        return {"success": False}

def write_float_real(addr, value):
    """
    Siemens REAL (FLOAT)
    - Holding registers
    - MS word first
    - Big endian
    """
    try:
        builder = BinaryPayloadBuilder(
            byteorder=Endian.Big,
            wordorder=Endian.Big
        )
        builder.add_32bit_float(float(value))
        regs = builder.to_registers()

        with lock:
            res = client.write_registers(addr - 40001, regs, unit=slave_id)

        return res and not res.isError()

    except Exception as e:
        print("WRITE FLOAT ERROR:", e)
        return False
@app.post("/write_impulse1_value")
async def write_impulse1_value(data: dict = Body(...)):
    try:
        key = data.get("key")
        value = data.get("value")

        if key not in read_address:
            return {"success": False, "error": "invalid key"}

        addr = read_address[key]

        # FLOAT (REAL)
        if key in ["imp1_max_press", "imp1_min_press"]:
            ok = write_float_real(addr, float(value))
            return {"success": ok}

        # UINT32
        if key == "imp1_cycles":
            v = int(value) & 0xFFFFFFFF
            lo = v & 0xFFFF
            hi = (v >> 16) & 0xFFFF

            with lock:
                res = client.write_registers(addr - 40001, [hi, lo], unit=slave_id)

            return {"success": res and not res.isError()}

        # UINT16 (rate & dwell)
        if key in [
            "imp1_max_rate",
            "imp1_min_rate",
            "imp1_max_dwell",
            "imp1_min_dwell"
        ]:
            v = int(value) & 0xFFFF
            with lock:
                res = client.write_register(addr - 40001, v, unit=slave_id)
            return {"success": res and not res.isError()}

        return {"success": False, "error": "unsupported key"}

    except Exception as e:
        print("IMPULSE WRITE ERROR:", e)
        return {"success": False}
@app.post("/write_stage_value")
async def write_stage_value(data: dict = Body(...)):
    try:
        key = data.get("key")
        if not key:
            return {"success": False, "error": "missing key"}

        raw_value = data.get("value")
        if raw_value is None:
            return {"success": False, "error": "missing value"}

        try:
            fval = float(raw_value)
        except:
            return {"success": False, "error": "invalid value"}

        # key → internal name mapping
        map_key = {
            "stage_count_set_a": "stage_count_set_a",
            "press_set_a": "press_set_a",
            "stage_cycles": "stage_cycles",
        }
        for i in range(1, 9):
            map_key[f"p{i}"] = f"stage_p{i}"
            map_key[f"r{i}"] = f"stage_r{i}"
            map_key[f"d{i}"] = f"stage_d{i}"

        if key not in map_key:
            return {"success": False, "error": "unknown key"}

        internal_key = map_key[key]
        addr = read_address.get(internal_key)
        if addr is None:
            return {"success": False, "error": "no address"}

        # ---------- UINT32 (cycles) ----------
        if internal_key == "stage_cycles":
            v = int(fval) & 0xFFFFFFFF
            lo = v & 0xFFFF
            hi = (v >> 16) & 0xFFFF

            with lock:
                res = client.write_registers(addr - 40001, [hi, lo], unit=slave_id)

            return {"success": res and not res.isError()}

        # ---------- FLOAT (REAL) ----------
        if internal_key in [
            "press_set_a",
            "stage_p1", "stage_p2", "stage_p3", "stage_p4",
            "stage_p5", "stage_p6", "stage_p7", "stage_p8"
        ]:
            ok = write_float_real(addr, fval)
            return {"success": ok}

        # ---------- UINT16 (rate & dwell) ----------
        ival = int(fval) & 0xFFFF
        with lock:
            res = client.write_register(addr - 40001, ival, unit=slave_id)

        return {"success": res and not res.isError()}

    except Exception as e:
        print("WRITE_STAGE_ERROR:", e)
        return {"success": False}

# Endpoint to write page number
@app.post("/page_change")
async def page_change(data: dict = Body(...)):
    page_no = int(data.get("page"))
    PAGE_REG = 40028   # INT32

    ok = write_int32(PAGE_REG, page_no)
    return {"success": ok, "page": page_no}
   
@app.post("/set_device_ip")
def set_device_ip(data: dict = Body(...)):
    ip = data.get("ip")
    if not ip:
        return {"success": False}

    ok = connect_plc(ip)
    return {"success": ok, "ip": ip if ok else None}


@app.get("/graph_data/{page}")
def graph_data(page: str):
    key = page_pressure_key.get(page)
    if not key:
        return {"time": 0, "pressure": 0}

    with lock:
        pressure = latest_data_1.get(key, 0)

    return {
        "time": time.time(),
        "pressure": pressure
    }

csv_manager = CSVManager()

@app.post("/csv_start/{page}")
def csv_start(page: str):
    csv_manager.start(page)
    return {"status": "started"}

@app.post("/csv_stop")
def csv_stop():
    csv_manager.stop()
    return {"status": "stopped"}

# @app.get("/indicator_state")
# def indicator_state():
#     return {
#         "state": bool(plc_connected),
#         "ip": plc_ip
#     }

@app.get("/csv_stream")
def csv_stream():
    global csv_read_offset

    with csv_lock:
        filename = current_csv_file

    if not filename or not os.path.exists(filename):
        return {"rows": []}

    rows = []

    with open(filename, "r") as f:
        f.seek(csv_read_offset)
        lines = f.readlines()
        csv_read_offset = f.tell()

    for line in lines:
        if line.startswith("timestamp"):
            continue
        ts, amp = line.strip().split(",")
        rows.append({
            "t": ts,
            "amp": float(amp)
        })

    return {"rows": rows}

@app.get("/csv_list")
def csv_list():
    files = []
    for f in os.listdir("logs"):
        if f.endswith(".csv"):
            files.append(f)
    files.sort(reverse=True)
    return {"files": files}


@app.get("/csv_data/{filename}")
def csv_data(filename: str):
    path = os.path.join("logs", filename)

    if not os.path.exists(path):
        return {"labels": [], "values": []}

    labels = []
    values = []

    with open(path, "r") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header

        for row in reader:
            if len(row) < 2:
                continue
            labels.append(row[0])        # timestamp
            values.append(float(row[1])) # amplitude

    return {
        "labels": labels,
        "values": values
    }

    
if __name__ == "__main__":
    import uvicorn
    import webview

    def start_server():
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False,log_level="warning" )

    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    saved_ip = load_last_ip()
    if saved_ip:
        connect_plc(saved_ip)
    
    webview.create_window("PNEUMATIC PRESSURE REGULATOR TEST RIG AUTOMATION", "http://127.0.0.1:8000", width=1200, height=800)

    webview.start()
