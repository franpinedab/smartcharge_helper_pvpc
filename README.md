# 🚗⚡ SmartCharge Helper PVPC - MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-purple.svg)](https://modelcontextprotocol.io/)

<div align="center">
  <img src="smartcharger.gif" alt="SmartCharger Demo" width="800"/>
</div>

> **Smart electric vehicle charging recommendations based on real-time Spanish PVPC electricity prices**

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that helps you find the cheapest hours to charge your electric vehicle using real-time Spanish electricity prices (PVPC).

## 🌟 Features

- **Real-time PVPC Prices**: Live electricity pricing from REE APIDATOS
- **Smart Charging Windows**: Find the best hours to charge your EV
- **Cost Calculations**: Accurate charging cost estimates
- **Docker Ready**: Easy deployment with Docker containers

## 🚀 Quick Start

**1. Clone & Build:**
```bash
git clone https://github.com/franpinedab/smartcharge_helper_pvpc.git
cd smartcharge_helper_pvpc
docker build -t smartcharge-helper-pvpc .
```

**2. Add to VS Code MCP (`mcp.json`):**
```json
{
  "servers": {
    "smartcharge-helper-pvpc": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "smartcharge-helper-pvpc"],
      "type": "stdio"
    }
  }
}
```


**SmartCharger Response:**
- **🌞 Best choice - Daytime (12:00-17:00):** 1.24€ (36 kWh)  
- **🌙 Alternative - Nighttime (03:00-08:00):** 5.48€  
- **❌ Avoid:** 21:00-23:00 (peak prices: 0.17-0.18€/kWh)

**💰 Savings:** 4.24€ by charging during solar hours!

## 🛠️ Development

**Requirements:** Python 3.12+ or Docker

```bash
# Without Docker (for development)
git clone https://github.com/franpinedab/smartcharge_helper_pvpc.git
cd smartcharge_helper_pvpc
pip install -r requirements.txt
python -m smartcharge_helper_pvpc
```

## 🔗 Links

- **Repository:** [franpinedab/smartcharge_helper_pvpc](https://github.com/franpinedab/smartcharge_helper_pvpc)
- **Data Source:** [REE APIDATOS](https://www.ree.es/es/apidatos) (Red Eléctrica de España)
- **MCP Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/)

## 📄 License

MIT License - see [LICENSE](LICENSE) file.



