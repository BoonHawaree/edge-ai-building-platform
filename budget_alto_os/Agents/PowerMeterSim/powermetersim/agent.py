import random
import time
import psycopg2
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core
import logging
from datetime import datetime

utils.setup_logging()
logger = logging.getLogger(__name__)

# Map meter_id to BRICK point_ids
METER_POINT_MAP = {
    1: 'pm_001_power',
    2: 'pm_002_power',
    3: 'pm_003_power',
    4: 'pm_004_power',
    5: 'pm_005_power',
}

class PowerMeterSimAgent(Agent):
    def __init__(self, config_path, **kwargs):
        super().__init__(**kwargs)
        self.meter_count = 5

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        while True:
            for meter_id in range(1, self.meter_count + 1):
                data = {
                    "meter_id": meter_id,
                    "power": round(random.uniform(0.5, 5.0), 2)  # kW
                }
                logger.info(f"⚡ Publishing data for meter {meter_id}: {data}")
                self.vip.pubsub.publish(
                    peer="pubsub",
                    topic=f"powermeter/{meter_id}",
                    message=data
                )

            time.sleep(15)

def main():
    utils.vip_main(PowerMeterSimAgent, version="0.1")

if __name__ == "__main__":
    main()