import random
import time
from datetime import datetime, timezone
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core

utils.setup_logging()

class HighCO2ScenarioAgent(Agent):
    def __init__(self, config_path, **kwargs):
        super().__init__(**kwargs)
        self.target_sensor = 8
        self.scenario_thread = None

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        # Start the scenario when the agent starts
        self.scenario_thread = self.core.spawn(self.trigger_high_co2_scenario)

    @Core.receiver("onstop")
    def onstop(self, sender, **kwargs):
        # Stop the scenario when the agent stops
        if self.scenario_thread:
            self.scenario_thread.kill()

    def trigger_high_co2_scenario(self):
        while True:
            # IAQ data
            for sensor_id in range(1, 11):
                if sensor_id == self.target_sensor:
                    data = {
                        "co2": random.randint(1250, 1400),
                        "temperature": 26.5,
                        "humidity": 45.0
                    }
                else:
                    data = {
                        "co2": random.randint(400, 700),
                        "temperature": round(random.uniform(21, 24), 2),
                        "humidity": round(random.uniform(40, 60), 2)
                    }
                self.vip.pubsub.publish("pubsub", f"iaq/{sensor_id}", message=data)

            # Power data (normal)
            for meter_id in range(1, 6):
                data = {"power": round(random.uniform(0.5, 5.0), 2)}
                self.vip.pubsub.publish("pubsub", f"powermeter/{meter_id}", message=data)

            time.sleep(15)

def main():
    utils.vip_main(HighCO2ScenarioAgent, version="0.1")

if __name__ == "__main__":
    main()