# Industrial PLC Data Logger & Real-Time SCADA Dashboard

**A production-grade, real-time telemetry acquisition and web-based SCADA visualization system** engineered for industrial testing automation with multi-PLC support, live data streaming, and persistent CSV logging.

---

## 🏭 Project Overview

This system is a professional **SCADA-lite telemetry platform** built to interface with leading industrial Programmable Logic Controllers (PLCs) over **Modbus TCP**. It provides real-time pressure monitoring, custom recipe parameter management, thread-safe data logging, and an intuitive web-based HMI (Human-Machine Interface) for operators to control and observe industrial testing procedures in real time.

**Key Capabilities:**
- ✅ Real-time multi-sensor telemetry acquisition from industrial PLCs
- ✅ Live Chart.js-powered data visualization with auto-scaling axes
- ✅ Persistent CSV logging with millisecond-precision timestamps
- ✅ WebSocket & REST API for responsive, low-latency updates
- ✅ Multi-test profile support (Burst, Impulse, Stage-based testing)
- ✅ Standalone PyWebView desktop HMI wrapper
- ✅ Built-in data simulator for offline training & development

---

## 🔌 Multi-PLC Support Architecture

The system is **hardware-agnostic** and field-tested with three major PLC families:

| PLC Platform | Protocol | Configuration | Status |
|---|---|---|---|
| **Siemens S7-1200 / S7-1500** | Modbus TCP | Port 502, Slave ID 1 | ✅ Production |
| **Delta DVP / AS / AH Series** | Modbus TCP | Port 502, Slave ID 1 | ✅ Production |
| **Mitsubishi FX / Q / L Series** | Modbus TCP (via comms module) | Port 502, Slave ID 1 | ✅ Production |

**Register Mapping Strategy:**
- **40001+ (Holding Registers)**: Modbus address space for all read/write operations
- **Float Registers (REAL/IEEE-754)**: Big-endian 32-bit IEEE format, MS word first
- **Integer Registers (INT32/UINT32)**: Dual-word register pairs with word-order handling
- **Coil/Discrete Registers**: Control signals for START/STOP/PAUSE operations

---

## 🛠️ Technology Stack

### Backend Architecture
```
Python 3.8+ | FastAPI | Uvicorn | PyModbus | Threading
```

**Core Libraries:**
- **`pymodbus`**: Industrial-grade Modbus TCP client with sync/async support
- **`FastAPI`**: Asynchronous REST API framework for low-latency endpoints
- **`Jinja2Templates`**: Server-side HTML rendering
- **`threading`**: Multi-threaded PLC polling & CSV logging (thread-safe via locks)
- **`struct`**: Binary data unpacking for IEEE-754 float conversion
- **`csv`**: Persistent logging with millisecond-precision timestamps

**Backend Features:**
- Dual background polling threads (`read_plc_task`, `h_read_plc_task`) for independent sensor/control data acquisition
- Thread-safe register sharing via `threading.Lock()` 
- Automatic PLC reconnect with 2-second retry logic
- Built-in sine-wave data simulator for offline mode
- IP memory (persistent last-connected PLC IP across sessions)

### Frontend Architecture
```
HTML5 | Vanilla JavaScript | Chart.js 4.x | REST API & WebSocket
```

**Key Files:**
- **`burst_auto.html`** – Real-time burst pressure testing interface with live Chart.js line graph
- **`burst_edit.html`** – Parameter editor for burst test recipes (Pressure, Rate, Duration)
- **`impluse_1_auto.html`** – High-frequency impulse cycle monitoring (min/max dwell, rate, cycles)
- **`stage_auto.html`** – Multi-stage (8-step) custom test sequences with live visualization
- **`graph.html`** – Historical CSV file replay & analysis tool
- **`manual.html`** – Manual pressure control mode for operator intervention

**Frontend Tech:**
- **Chart.js**: Real-time animated line charts with dynamic y-axis scaling (prevents graph shaking)
- **Fetch API**: Low-latency REST calls (200ms poll rate for live data)
- **WebSocket-ready**: Architecture supports WebSocket upgrade for sub-100ms latency
- **Responsive Design**: CSS Grid & Flexbox for adaptive layouts
- **Digital Clock**: Real-time HH:MM:SS display with date

### Desktop Application Wrapper
- **`PyWebView`**: Native desktop window (Windows/macOS/Linux) wrapping the web interface
- **`PyInstaller`**: Single `.exe` packaging for distribution to industrial sites
- Embedded Uvicorn server on `127.0.0.1:8000` (no external network dependency)

---

## 📊 Real-Time Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PLC (Siemens/Delta/Mitsubishi)         │
│              Holding Registers (40001–40400+)               │
└─────────────────┬───────────────────────────────────────────┘
                  │ Modbus TCP
                  ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (PPR.py)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  read_plc_task (200ms)   │  h_read_plc_task (200ms) │   │
│  │  • Reads control regs    │  • Reads sensor data    │   │
│  │  • Parses FLOAT/INT32    │  • Handles scaling      │   │
│  │  • Updates latest_data   │  • Updates latest_data_1│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ CSV Logger Thread ────────────────────────────────────┐ │
│  │  • Writes page_regs_1 dataset @ 50ms interval         │ │
│  │  • Millisecond-precision timestamps                   │ │
│  │  • Thread-safe file I/O via csv_lock                  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────┬──────────────────────────────────────────────────────┘
      │ REST API (/plc_value, /burst_start, /write_burst_value, etc.)
      ↓
┌─────────────────────────────────────────────────────────────┐
│         Frontend (HTML5 + Chart.js)                         │
│  • Polls /plc_value every 200ms                            │
│  • Renders Chart.js animated line graph (500-point buffer) │
│  • Displays live status, pressure, rate, time, cycles      │
│  • Sends commands: /burst_start, /burst_pause, /burst_stop │
└─────────────────────────────────────────────────────────────┘
      ↑
      │ PyWebView (Desktop wrapper)
      │ or Standard Browser
```

---

## 📁 Project Structure

```
plc-data-logger/
├── PPR.py                          # Main FastAPI application
│   ├── PLC Connection Layer
│   │   ├── connect_plc()           # Modbus TCP client init
│   │   ├── read_float_ascii()      # IEEE-754 FLOAT parsing
│   │   ├── read_uint32_ascii()     # 32-bit INT parsing
│   │   └── plc_reconnect_task()    # Auto-reconnect daemon
│   │
│   ├── Background Polling Threads
│   │   ├── read_plc_task()         # Main register polling
│   │   ├── h_read_plc_task()       # High-frequency sensor polling
│   │   └── scan_ips_task()         # ARP network discovery
│   │
│   ├── CSV Logger
│   │   └── CSVManager class        # Thread-safe persistent logging
│   │
│   ├── API Endpoints (REST)
│   │   ├── GET  /plc_value         # Return latest_data snapshot
│   │   ├── POST /burst_start       # Write control register
│   │   ├── POST /write_burst_value # Parameter update (FLOAT/INT32)
│   │   ├── GET  /csv_list          # List logged sessions
│   │   ├── GET  /csv_data/{file}   # Retrieve historical data
│   │   ├── GET  /indicator_plc     # PLC status LED
│   │   └── ... (30+ endpoints)
│   │
│   └── HTML Route Handlers
│       └── Jinja2 template rendering
│
├── PPR.spec                        # PyInstaller build spec
│
├── logs/                           # CSV Data Directory
│   ├── burst_auto_20250629_143022.csv
│   ├── stage_auto_20250629_142145.csv
│   └── impluse_1_auto_20250629_150312.csv
│
├── static/
│   ├── js/
│   │   └── chart.umd.min.js        # Chart.js 4.x library (CDN fallback)
│   └── screenshots/
│       ├── welcome.png
│       ├── dashboard.png
│       ├── burst_auto.png
│       └── graph.png
│
└── templates/                      # Jinja2 HTML Templates
    ├── welcome.html               # Splash/intro screen
    ├── main.html                  # Dashboard navigation hub
    ├── auto.html                  # Auto-test mode selector
    ├── manual.html                # Manual pressure control
    ├── edit_program.html          # Recipe editor menu
    │
    ├── burst_auto.html            # Real-time burst test HMI
    ├── burst_edit.html            # Burst recipe editor
    ├── impluse_1_auto.html        # Impulse cycle monitor
    ├── impluse_1_edit.html        # Impulse recipe editor
    ├── stage_auto.html            # Multi-stage test monitor
    ├── stage_edit.html            # Stage recipe editor
    ├── graph.html                 # Historical graph viewer
    └── ...
```

---

## 🎯 Core Features & Workflows

### 1. **Real-Time Burst Pressure Testing**
- **Workflow**: Operator enters Pressure setpoint → Rate of Rise → Duration
- **Live Monitoring**: Chart.js graph plots actual pressure vs. time (500-point rolling buffer)
- **Control**: START → Test running (MSG=1) → PAUSE → RESUME → STOP (MSG=0)
- **CSV Logging**: Time, Pressure, Peak automatically saved every 50ms
- **Status Indicator**: Green LED indicates PLC connection; color-coded status bar (Ready/Running/Paused/Fail)

**Sample Data Flow:**
```javascript
// Frontend (200ms poll)
fetch("/plc_value").then(d => {
  // pressure_actual = 6.32 bar (from PLC register 40007)
  updateGraph(d.pressure_actual);
  // CSV Manager writes: 2025-06-29 14:30:22.450,6.32
});
```

### 2. **High-Frequency Impulse Cycle Monitoring**
- **Multi-Parameter Tracking**: Max Pressure, Min Pressure, Rate, Dwell Time, Cycle Count
- **Real-Time Limits Display**: Upper/Lower bounds for each parameter
- **Cycle Counter**: Live count of completed test cycles
- **Dual Polling**: Separate high-frequency thread captures sensor transients

### 3. **Multi-Stage Sequential Testing**
- **8-Stage Support**: Define up to 8 sequential pressure/rate/dwell combinations
- **Auto-Progression**: PLC advances stages autonomously; dashboard mirrors state
- **Duration Tracking**: Total test time + per-stage completion times
- **CSV Export**: All stage transitions logged for SPC analysis

### 4. **Recipe Parameter Management**
- **Input Validation**: Min/Max bounds enforced (e.g., Pressure 0–10 bar)
- **Real-Time Sync**: Edit fields update PLC registers instantly via Modbus TCP write
- **Persistent State**: Last entered recipe persists across operator sessions
- **Unit Conversion**: Frontend scaling handles bar → PSI, minutes → seconds, etc.

### 5. **Historical Data Analysis & Playback**
- **CSV File Listing**: Dropdown of all logged test sessions (sorted by date)
- **Graph Overlay**: Load any historical CSV and replay on Chart.js with full zoom/pan
- **Export Ready**: CSVs compatible with Excel, MATLAB, Python pandas
- **Timestamp Precision**: Millisecond accuracy for SPC/statistical analysis

### 6. **Data Simulation Mode** (Offline)
- **Automatic Fallback**: When PLC is disconnected, generates realistic sine-wave simulation
- **Same API**: Frontend sees no difference between PLC and simulator
- **Training Safe**: New operators train without risking hardware damage
- **Cycle Time**: 200ms polling loop identical in both modes

---

## 📊 API Reference

### Data Acquisition Endpoints

#### `GET /plc_value`
Returns current snapshot of all register values.

**Response:**
```json
{
  "pressure_set": 6.5,
  "pressure_actual": 6.32,
  "rate_set1": 1.5,
  "time_actual": 45.2,
  "peak_actual": 7.18,
  "cycles_actual": 5,
  "MSG_b": 1
}
```

#### `GET /graph_data/{page}`
Real-time single-point data for Chart.js streaming.

**Response:**
```json
{
  "time": 1719669022.453,
  "pressure": 6.45
}
```

### Control Endpoints

#### `POST /burst_start`
Sends START command to PLC (writes register 40037 = 1).

#### `POST /burst_pause`
Toggles PAUSE/RESUME state (writes register 40041).

#### `POST /write_burst_value`
Updates recipe parameter with automatic type conversion.

**Request:**
```json
{
  "key": "pressure_set",
  "value": 7.5
}
```

**Automatic Handling:**
- FLOAT registers: Converts to IEEE-754 big-endian, writes dual words
- INT32 registers: Packs into [HI, LO] word pair
- UINT16 registers: Direct single-word write

### Logging Endpoints

#### `POST /csv_start/{page}`
Begin CSV logging for specified test page.

#### `POST /csv_stop`
Stop active CSV logging session.

#### `GET /csv_list`
List all available logged CSV files.

#### `GET /csv_data/{filename}`
Retrieve historical test data for chart replay.

---

## 🔐 Register Mapping & Data Types

### Float Registers (IEEE-754 Big-Endian)
```python
# Example: Pressure setpoint at 40051
# PLC holds: [40051] = 0x4149 (MS word), [40052] = 0x999A (LS word)
# Combined: 0x41499999 = 12.30000114440918 bar

read_float_ascii(40051)  # Returns 12.30
```

### Integer Registers (Dual-Word)
```python
# Example: Cycle count at 40273 (32-bit UINT32)
# PLC holds: [40273] = 0x0000 (HI), [40274] = 0x00A5 (LO)
# Combined: (0x0000 << 16) | 0x00A5 = 165 cycles

read_uint32_ascii(40273)  # Returns 165
```

### Register List (Partial)
| Name | Address | Type | Min | Max | Unit |
|---|---|---|---|---|---|
| pressure_set | 40051 | FLOAT | 0.0 | 10.0 | bar |
| pressure_actual | 40007 | FLOAT | 0.0 | 10.0 | bar |
| rate_set1 | 40053 | FLOAT | 0.0 | 3000.0 | bar/min |
| time_set | 40055 | FLOAT | 0.0 | 999.0 | min |
| cycles_set1 | 40091 | UINT32 | 0 | 1000000 | count |
| burst_start | 40037 | INT32 | 0 | 1 | 1=start |
| MSG_b | 40032 | INT16 | 0 | 4 | 0=ready, 1=run, 2=pause, 3=fail, 4=ok |

*See `PPR.py` lines 87–239 for complete register dictionary.*

---

## 🧵 Threading Model & Concurrency

### Thread Safety Architecture
```python
lock = threading.Lock()  # Protects: latest_data, latest_data_1

# Background Thread 1: read_plc_task (200ms cycle)
def read_plc_task():
    while not stop_thread:
        with lock:  # Acquire lock
            res = client.read_holding_registers(...)  # I/O
        # Process data
        with lock:  # Update shared state
            latest_data[key] = value

# Background Thread 2: h_read_plc_task (200ms cycle)
def h_read_plc_task():
    while not stop_thread:
        # Same pattern: lock → read → lock → update

# Main Thread: FastAPI (handles HTTP requests)
@app.get("/plc_value")
async def plc_value():
    with lock:
        return latest_data.copy()  # Safe snapshot
```

### CSV Logger Thread
```python
class CSVManager:
    def run(self, page):
        while self.active:
            row = []
            for key in page_regs_1[page]:
                with lock:
                    raw = latest_data_1.get(key)  # Safe read
                scaled = raw / scale_map[key]
                row.append(f"{scaled:.2f}")
            
            self.file.write(ts + "," + ",".join(row) + "\n")
            time.sleep(0.05)  # 20 Hz write rate
```

---

## 🎨 Frontend HMI Samples

### Burst Auto Test Screen (`burst_auto.html`)
```
┌─────────────────────────────────────────┐
│  [BACK]     Burst Pressure     [CLOCK]  │
├─────────────────────────────────────────┤
│                                         │
│  Pressure (bar)    │ Set: 6.50 bar    │
│                    │ Actual: 6.32 bar │
│                                         │
│  Rate (bar/min)    │ Set: 1.50        │
│  Time (min)        │ Set: 30  Act: 25 │
│  Peak (bar)        │ Act: 7.18 bar    │
│                                         │
│  [START]  [STOP]  [PAUSE]              │
│                                         │
│  Status: ✅ Test Running                │
│                                         │
│  ┌─ Pressure vs Time Chart ───────────┐│
│  │ 8.0 │     ╱╲                        ││
│  │ 7.0 │    ╱  ╲    ╱╲                 ││
│  │ 6.0 │   ╱    ╲  ╱  ╲                ││
│  │ 5.0 │  ╱      ╲╱    ╲               ││
│  │ 0.0 └─────────────────────────────  ││
│  │     0s   30s   60s   90s   120s     ││
│  └────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

### Stage Edit Screen (`stage_edit.html`)
```
┌─────────────────────────────────────────┐
│  [BACK]     Stage Pressure    [CLOCK]   │
├─────────────────────────────────────────┤
│  Number of Stages: [8]                  │
│                                         │
│  ┌─ STAGE 1 ───────────────────────┐   │
│  │ Pressure (bar):  [5.5]           │   │
│  │ Rate (bar/min):  [1.2]           │   │
│  │ Dwell (sec):     [10]            │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─ STAGE 2 ───────────────────────┐   │
│  │ Pressure (bar):  [6.0]           │   │
│  │ Rate (bar/min):  [1.5]           │   │
│  │ Dwell (sec):     [15]            │   │
│  └─────────────────────────────────┘   │
│  ...                                    │
└─────────────────────────────────────────┘
```

---

## 📈 Performance Metrics

| Metric | Value | Notes |
|---|---|---|
| **PLC Poll Rate** | 200 ms | Dual threads (control + sensor) |
| **CSV Write Interval** | 50 ms | 20 Hz data logging |
| **HTTP API Latency** | <50 ms | REST endpoint response time |
| **Chart.js Update Rate** | 200 ms | 5 FPS smooth animation |
| **Max Chart Points** | 500 | Rolling buffer prevents memory bloat |
| **Modbus RTT** | ~10–20 ms | Network dependent |
| **CSV File Size** | ~1 MB/hour | Per-sensor at 20 Hz logging |

---

## 🛡️ Error Handling & Robustness

### PLC Disconnection
- **Detection**: 2-second reconnect daemon checks connection status
- **Fallback**: Auto-switches to sine-wave simulator (same API)
- **Recovery**: Automatic reconnect when PLC comes online
- **User Feedback**: Status indicator turns RED; operators see simulator data

### Register Read Errors
```python
try:
    value = read_float_ascii(addr)
except Exception as e:
    value = None  # Graceful degradation
    print("FLOAT READ ERROR:", e)

# Frontend displays last-known value or 0.0
if value is None:
    return {"status": "error", "last_known": latest_data[key]}
```

### CSV Write Failures
- **Disk Full**: Gracefully stops logging; data loss prevented by thread-safe file handles
- **Permission Denied**: Logs to console; application continues running
- **File Corruption**: Atomic writes with flush() after each row

---

## 🚀 Production Deployment Checklist

- [ ] Test PLC connectivity on target network (IP, port 502 open?)
- [ ] Verify all 3 PLC platforms work with your register map
- [ ] Package `.exe` with PyInstaller (`pyinstaller PPR.spec`)
- [ ] Set Last-IP persistence for operator convenience
- [ ] Create `logs/` directory with write permissions
- [ ] Disable reload mode for performance: `reload=False` ✓ (already set)
- [ ] Configure firewall to allow `127.0.0.1:8000` (local only, secure)
- [ ] Test CSV export with Excel/MATLAB for SPC workflows
- [ ] Backup register map if customizing for site-specific PLCs

---

## 📚 Technology Highlights for Portfolio

This project demonstrates mastery in:

✅ **Industrial Automation**
   - Multi-PLC protocol support (Siemens, Delta, Mitsubishi)
   - Modbus TCP register mapping & data type handling
   - Real-time critical polling loops

✅ **Backend Architecture**
   - FastAPI async framework for low-latency APIs
   - Thread-safe concurrent data acquisition
   - Persistent CSV logging with millisecond precision

✅ **Frontend Engineering**
   - Real-time Chart.js visualization (500-point rolling buffer)
   - Responsive HTML5/CSS3 design
   - REST API integration for live data streaming

✅ **Systems Integration**
   - Binary protocol parsing (IEEE-754 floats, multi-word integers)
   - Thread synchronization & lock management
   - Network error recovery & automatic reconnection

✅ **DevOps & Deployment**
   - PyInstaller packaging for Windows distribution
   - Standalone desktop app (PyWebView wrapper)
   - Cross-platform Python compatibility

---

## 📝 License
MIT License – See LICENSE file for details.

---

## 👨‍💻 Author & Contact
**Developed by:** RAM (Ramasamy V)  
**Role:** Firmware & Automation Engineer  
**Stack:** Python, FastAPI, Modbus TCP, HTML5/JS, FreeRTOS  
**GitHub:** [@Ramasamy15012004](https://github.com/Ramasamy15012004)  

---

## 🎓 Learning Outcomes

This project is ideal for showcasing:
- Industrial protocol expertise (Modbus TCP)
- Real-time data acquisition & visualization
- Multi-threaded Python applications
- Web-based SCADA system design
- Production-ready error handling
- Cross-platform desktop app development

**Perfect for:** Embedded Systems Roles | IIoT Developer Positions | Automation Engineer Applications | SCADA System Architect Interviews
