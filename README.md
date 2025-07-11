# 🚗 SmartCharge Helper PVPC - MCP Server

> **Smart electric vehicle charging recommendations based on real-time Spanish PVPC electricity prices**

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides intelligent charging recommendations for electric vehicles using live electricity pricing data from the Spanish market (PVPC).

## Features

- **Real-time PVPC Prices**: Live electricity pricing from REE APIDATOS
- **Smart Charging Windows**: Find the best hours to charge your EV
- **Cost Calculations**: Accurate charging cost estimates
- **Docker Ready**: Easy deployment with Docker containers

## 🚀 Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/smartcharge-helper-pvpc.git
cd smartcharge-helper-pvpc

# Build and run with Docker
docker build -t smartcharge-helper-pvpc .
docker run -it smartcharge-helper-pvpc

# Or use docker-compose
docker-compose up
```

### VS Code Integration

**Option 1: Using Docker (Recommended)**
```json
{
  "servers": {
    "charging-advisor": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "smartcharge-helper-pvpc"
      ],
      "type": "stdio"
    }
  }
}
```

**Option 2: Using Local Python**
```json
{
  "servers": {
    "charging-advisor": {
      "command": "python",
      "args": ["-m", "smartcharge_helper_pvpc"],
      "cwd": "/path/to/smartcharge-helper-pvpc",
      "type": "stdio"
    }
  }
}
```

### Local Installation (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m smartcharge_helper_pvpc
```

## Available Tools

### `get_current_pvpc_prices`
Get current electricity prices for any date.

### `get_best_charging_hours`
Find optimal charging windows based on electricity prices.

##  Example Usage

### Real-world Scenario: Tesla Model 3 Charging

Best charging window: 01:00 - 08:00  
Estimated cost: 6.42€ (50 kWh)  
Average price: 0.1283€/kWh  
Savings vs peak hour: 1.41€ (18% cheaper)

##  License

This project is licensed under the MIT License.

---

