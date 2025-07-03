# **Edge AI Platform for Building Energy & IAQ Optimization**

This repository contains a production-ready Edge AI platform that deploys LLMs on-premise to analyze real-time IoT data from building systems (IAQ sensors and power meters), provide intelligent recommendations, and autonomously optimize building operations.

The platform is built on the Eclipse VOLTTRON™ framework and includes:
- TimescaleDB agent for time-series data storage with BRICK schema annotations
- Mock data generation for IAQ sensors and power meters
- LLM integration for intelligent building automation recommendations
- Real-time data streaming and historical data access

## **Setup Instructions**

### Prerequisites
- Docker and Docker Compose
- Git
- NVIDIA GPU with CUDA support (for LLM deployment)

### Setup VOLTTRON
Clone the official VOLTTRON repository in the project working directory:

```bash
# Clone VOLTTRON from official repository
git clone https://github.com/VOLTTRON/volttron.git
```

## **Running the Platform with Docker**

### Quick Start
To run the VOLTTRON platform with the TimescaleDB agent:

```bash
# Start the platform
docker compose up -d --build

# Monitor logs
docker logs alto_os -f
```

The platform includes a pre-configured TimescaleDB agent that you can use out of the box for storing IoT sensor data with proper BRICK schema annotations.

### Platform Access and Management

Access the VOLTTRON platform container:
```bash
docker exec -itu volttron alto_os bash
```

Check platform status:
```bash
vctl status
```

Monitor specific agent logs:
```bash
docker logs alto_os --follow 2>&1 | grep --line-buffered <agent-tag>
```

## **Available Components**

### TimescaleDB Agent
The repository includes a pre-built TimescaleDB agent located at:
```bash
./Agents/TimescaleDB/
```

This agent provides:
- Time-series data storage optimized for IoT sensor data
- BRICK schema annotations for building automation data
- Real-time data ingestion capabilities
- Historical data query support

### Key Directories

1. **Agents**: Custom VOLTTRON agents
    ```bash
    cd /code/volttron/Agents
    ```

2. **Site Configurations**: Platform configuration files
    ```bash
    cd /code/volttron/site_configs
    ```

### Agent Management

Reinstall agents (useful for configuration updates):
```bash
docker exec -itu volttron alto_os bash
python3 /startup/reinstall-agents.py
```

### Troubleshooting

**Line Ending Issues**: If the build process fails, ensure text files use `LF` line endings:
```bash
sudo apt-get install dos2unix
find . -type f -print0 | xargs -0 dos2unix
```

## **Development Environment Setup**

For local development without Docker:

### 1. Setup VOLTTRON
```bash
cd volttron
python3 bootstrap.py --web
```

### 2. Activate Virtual Environment
```bash
source env/bin/activate
```
*Note: Configure your IDE to use this virtual environment*

### 3. Start VOLTTRON Platform
```bash
cd Agents
volttron --bind-web-address http://0.0.0.0:<port> -vv -l volttron.log&
```

### 4. Verify Installation
```bash
vctl status
```
*Expected output: `NO INSTALLED AGENT` indicates the platform is ready*

## **Test Environment Overview**

This repository is designed for building an Edge AI platform with the following capabilities:

### Core Features
- **LLM Integration**: Deploy open-source LLMs (NVIDIA Nemotron, Llama 3.1, Mistral, etc.) for building automation
- **IoT Data Processing**: Handle real-time data from IAQ sensors and power meters
- **TimescaleDB Storage**: Pre-configured agent for time-series data with BRICK schema
- **Intelligent Recommendations**: AI-powered building optimization suggestions

### Use Cases Supported
1. **Proactive IAQ Optimization**: Real-time air quality monitoring and recommendations
2. **Energy Waste Detection**: Automated detection and prevention of energy overconsumption
3. **Building Operations Optimization**: AI-driven operational efficiency improvements

### Data Sources
- **IAQ Sensors**: CO₂, temperature, humidity (30-second intervals)
- **Power Meters**: Real-time energy consumption (15-second intervals)
- **Historical Data**: Full access through TimescaleDB for trend analysis

The platform provides a foundation for implementing Edge AI solutions in building automation, with pre-built components for data ingestion, storage, and the infrastructure needed for LLM integration.