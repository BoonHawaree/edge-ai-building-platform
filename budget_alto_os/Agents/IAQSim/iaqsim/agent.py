import random
import time
import psycopg2
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, PubSub
import logging
from datetime import datetime, timezone

utils.setup_logging()
logger = logging.getLogger(__name__)

# Map sensor_id to BRICK point_ids
SENSOR_POINT_MAP = {
    1: {'co2': 'iaq_001_co2', 'temperature': 'iaq_001_temp', 'humidity': 'iaq_001_humid'},
    2: {'co2': 'iaq_002_co2', 'temperature': 'iaq_002_temp', 'humidity': 'iaq_002_humid'},
    3: {'co2': 'iaq_003_co2', 'temperature': 'iaq_003_temp', 'humidity': 'iaq_003_humid'},
    4: {'co2': 'iaq_004_co2', 'temperature': 'iaq_004_temp', 'humidity': 'iaq_004_humid'},
    5: {'co2': 'iaq_005_co2', 'temperature': 'iaq_005_temp', 'humidity': 'iaq_005_humid'},
    6: {'co2': 'iaq_006_co2', 'temperature': 'iaq_006_temp', 'humidity': 'iaq_006_humid'},
    7: {'co2': 'iaq_007_co2', 'temperature': 'iaq_007_temp', 'humidity': 'iaq_007_humid'},
    8: {'co2': 'iaq_008_co2', 'temperature': 'iaq_008_temp', 'humidity': 'iaq_008_humid'},
    9: {'co2': 'iaq_009_co2', 'temperature': 'iaq_009_temp', 'humidity': 'iaq_009_humid'},
    10: {'co2': 'iaq_010_co2', 'temperature': 'iaq_010_temp', 'humidity': 'iaq_010_humid'},
}

class IAQSimAgent(Agent):
    def __init__(self, config_path, **kwargs):
        super().__init__(**kwargs)
        self.sensor_count = 10

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        while True:
            for sensor_id in range(1, self.sensor_count + 1):
                data = {
                    "sensor_id": sensor_id,
                    "co2": random.randint(400, 1000),
                    "temperature": round(random.uniform(20, 30), 2),
                    "humidity": round(random.uniform(30, 70), 2),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                logger.info(f"🌡️ Publishing data for sensor {sensor_id}: {data}")
                self.vip.pubsub.publish(
                    peer="pubsub",
                    topic=f"iaq/{sensor_id}",
                    message=data
                )
            time.sleep(30)

def main():
    utils.vip_main(IAQSimAgent, version="0.1")

if __name__ == "__main__":
    main()