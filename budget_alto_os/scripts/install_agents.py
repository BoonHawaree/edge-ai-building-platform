import argparse
import subprocess
import time
import yaml
import os

AGENT_NAME_TO_PATH = {
    "bacnet": "Devices/BACnet",
    "platform_agent": "Platforms/PlatformAgent",
    "load_forecast": "Applications/LoadForecastAgent",
    "firebase": "Services/Firebase",
    "chillerplantoptimization": "Services/ChillerPlantOptimization",
    "mongodb": "Services/MongoDB",
    "afdd": "Applications/AFDD",
    "weathertmd": "Services/WeatherTMD",
    "weatherforecast": "Services/WeatherForecast",
    "chiller_prediction": "Services/ChillerPrediction",
    "timescaledb": "Services/TimescaleDB",
    "dataforwarder": "Services/DataForwarder",
    "dataintegrity": "Services/DataIntegrity",
    "azureiothub": "Services/AzureIoTHub",
    "gatewaystatus": "Services/GatewayStatus",
    "ahu": "Devices/AHU",
    "chilleraddsubtract": "Applications/ChillerAddSubtract",
    "chillerplantschedule": "Applications/ChillerPlantSchedule",
    "chillersequence": "Applications/ChillerSequence",
    "schpcontrol": "Applications/SCHPControl",
    "linenotification": "Services/LineNotification",
    "uihelper": "Applications/UIHelper",
    "smartct": "Applications/SmartCT",
    "supabase": "Services/Supabase",
    "controlschedule": "Applications/ControlSchedule",
    "mockbacnet": "Devices/MockBACnet",
    "virtualpoints": "Services/VirtualPoints",
    "modbus": "Devices/Modbus",
    "hikvision": "Devices/Hikvision",
    "backendgateway": "Services/BackendGateway",
    "loragatewaymqtt": "Devices/LoRaGatewayMQTT",
}


if __name__ == "__main__":

    # Set up argparse to accept the site_id and site_config_dir arguments
    parser = argparse.ArgumentParser(
        description="Install Volttron agents with specified configuration."
    )
    parser.add_argument(
        "site_id", type=str, help="Id of the site configuration to use."
    )
    parser.add_argument(
        "--site_config_dir",
        type=str,
        default=os.getcwd(),
        help="Directory containing site config files (default: current directory)",
    )

    # Parse the arguments and load config file
    args = parser.parse_args()
    SITE_ID = args.site_id
    SITE_CONFIG_DIR = args.site_config_dir
    SITE_CONFIG_PATH = os.path.join(SITE_CONFIG_DIR, f"{SITE_ID}.yaml")

    if not os.path.exists(SITE_CONFIG_PATH):
        print(f"Error: Site config file not found at {SITE_CONFIG_PATH}")
        exit(1)

    site_config = yaml.safe_load(open(SITE_CONFIG_PATH, "r"))

    print(f"Installing Volttron agents with config: {SITE_CONFIG_PATH}")

    # Iterate over the agent_list and install each agent
    installed_agents = site_config["deployment_config"]["installed_agents"]
    for agent_name, enabled in installed_agents.items():
        agent_name = agent_name.upper().replace("AGENT", "-AGENT")
        if enabled:
            print(f"✅ {agent_name}")
        else:
            print(f"❌ {agent_name}")

    for agent_name, enabled in installed_agents.items():

        if not enabled:
            print(f"Skipping {agent_name} because it is not enabled....")
            continue

        agent_path = AGENT_NAME_TO_PATH.get(agent_name, None)
        if agent_path is None:
            print(f"Agent {agent_name} not found in AGENT_NAME_TO_PATH")
            continue

        print(f"Installing {agent_name}")
        subprocess.run(f"vctl remove --tag {agent_name}", shell=True)
        time.sleep(2)
        subprocess.run(
            f'vctl config store {agent_name} config "{SITE_CONFIG_PATH}" --raw',
            shell=True,
        )
        install_command = (
            f"vctl install \"{os.path.join(os.path.dirname(__file__), '..', 'Agents', agent_path)}\" "
            f"--tag {agent_name} --vip-identity {agent_name} "
            f'--agent-config "{SITE_CONFIG_PATH}" '
            f"--enable"
        )
        time.sleep(2)
        subprocess.run(install_command, shell=True)
