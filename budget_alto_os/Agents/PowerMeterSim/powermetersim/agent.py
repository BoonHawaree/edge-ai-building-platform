import random
import time
from datetime import datetime, timezone
from volttron.platform.agent import utils
from volttron.platform.vip.agent import Agent, Core, PubSub
import logging

utils.setup_logging()
logger = logging.getLogger(__name__)

# Realistic power meter ranges (kW) from seed_historical_data.py
POWER_RANGES = {
    'pm_001': {'min': 15, 'max': 45, 'name': 'Floor_1'},
    'pm_002': {'min': 12, 'max': 38, 'name': 'Floor_2'},
    'pm_003': {'min': 30, 'max': 85, 'name': 'Main_Building'},
    'pm_004': {'min': 20, 'max': 100, 'name': 'Chiller'},
    'pm_005': {'min': 2, 'max': 8, 'name': 'Elevator'}
}

class PowerMeterSimAgent(Agent):
    def __init__(self, config_path, **kwargs):
        super().__init__(**kwargs)
        self.meter_count = 5

    def _generate_realistic_power(self, meter_id: int, timestamp: datetime) -> float:
        """
        Generates realistic power consumption based on time of day, day of week,
        and meter type, adapted from seed_historical_data.py.
        """
        hour = timestamp.hour
        weekday = timestamp.weekday()  # Monday is 0 and Sunday is 6
        meter_key = f'pm_{meter_id:03d}'

        meter_info = POWER_RANGES.get(meter_key)
        if not meter_info:
            return round(random.uniform(0.5, 5.0), 2) # Fallback for unknown meter

        min_power = meter_info['min']
        max_power = meter_info['max']
        base_factor = 0.2  # Default base factor for after hours

        if meter_key == 'pm_004':  # Chiller - weather dependent
            if 10 <= hour <= 18:
                base_factor = 0.7 + random.uniform(0, 0.3)  # High cooling load
            elif 6 <= hour <= 22:
                base_factor = 0.5 + random.uniform(0, 0.2)
            else:
                base_factor = 0.3 + random.uniform(0, 0.1)  # Night setback

        elif meter_key == 'pm_005':  # Elevator - occupancy dependent
            if weekday < 5:  # Weekday
                if 8 <= hour <= 18:
                    base_factor = 0.6 + random.uniform(0, 0.4)  # Busy periods
                else:
                    base_factor = 0.1 + random.uniform(0, 0.1)
            else:  # Weekend
                base_factor = 0.2

        else:  # Floor meters (pm_001, pm_002, pm_003) - occupancy dependent
            if weekday < 5:  # Weekday
                if 9 <= hour <= 17:
                    base_factor = 0.6 + random.uniform(0, 0.3)  # Business hours
                elif hour in [8, 18]:
                    base_factor = 0.5 + random.uniform(0, 0.2)  # Transition
                else:
                    base_factor = 0.2 + random.uniform(0, 0.1)  # After hours
            else:  # Weekend
                base_factor = 0.3

        power = min_power + (max_power - min_power) * base_factor
        power += random.uniform(-2, 2)  # Add some random variation

        # Ensure power is not unrealistically low, but can be 0 if meter is off
        return round(max(0, power), 2)

    @Core.receiver("onstart")
    def onstart(self, sender, **kwargs):
        while True:
            for meter_id in range(1, self.meter_count + 1):
                now = datetime.now(timezone.utc)
                power_value = self._generate_realistic_power(meter_id, now)
                data = {
                    "meter_id": meter_id,
                    "power": power_value,
                    "timestamp": now.isoformat()
                }
                logger.info(f"⚡ Publishing data for meter {meter_id}: {data}")
                self.vip.pubsub.publish(
                    peer="pubsub",
                    topic=f"powermeter/{meter_id}",
                    message=data
                )
            time.sleep(30) # Publish every 30 seconds for all meters

def main():
    utils.vip_main(PowerMeterSimAgent, version="0.1")

if __name__ == "__main__":
    main()