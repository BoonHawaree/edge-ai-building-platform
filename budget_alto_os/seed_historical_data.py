#!/usr/bin/env python3
"""
Historical Building Data Seeding Script
Generates 3 days of realistic building automation data for demo

Building Structure:
- Floor 1: Lobby (1_1), Conference (1_2), Restaurant (1_3), Co-working (1_4, 1_5)
- Floor 2: Offices (2_1, 2_2, 2_3), Co-working (2_4, 2_5)

Power Meters:
- pm_001: Floor 1 (15-45kW typical)
- pm_002: Floor 2 (12-38kW typical)  
- pm_003: Main Building (30-85kW total)
- pm_004: Chiller (20-80kW - highest consumer)
- pm_005: Elevator (2-8kW)
"""

import asyncpg
import asyncio
from datetime import datetime, timedelta
import random
import math

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'Magicalmint@636',
    'port': 5432
}

class BuildingDataSeeder:
    def __init__(self):
        self.connection = None
        
        # Zone definitions with realistic characteristics
        self.zones = {
            'zone_1_1': {'name': 'Lobby', 'type': 'public', 'base_occupancy': 0.3},
            'zone_1_2': {'name': 'Conference', 'type': 'meeting', 'base_occupancy': 0.1}, 
            'zone_1_3': {'name': 'Restaurant', 'type': 'dining', 'base_occupancy': 0.2},
            'zone_1_4': {'name': 'Co-working_1', 'type': 'flexible', 'base_occupancy': 0.4},
            'zone_1_5': {'name': 'Co-working_2', 'type': 'flexible', 'base_occupancy': 0.4},
            'zone_2_1': {'name': 'Office_1', 'type': 'office', 'base_occupancy': 0.6},
            'zone_2_2': {'name': 'Office_2', 'type': 'office', 'base_occupancy': 0.6},
            'zone_2_3': {'name': 'Office_3', 'type': 'office', 'base_occupancy': 0.6},
            'zone_2_4': {'name': 'Co-working_3', 'type': 'flexible', 'base_occupancy': 0.4},
            'zone_2_5': {'name': 'Co-working_4', 'type': 'flexible', 'base_occupancy': 0.4}
        }
        
        # Power meter realistic ranges (kW)
        self.power_ranges = {
            'pm_001': {'min': 15, 'max': 45, 'name': 'Floor_1'},      # Floor 1
            'pm_002': {'min': 12, 'max': 38, 'name': 'Floor_2'},      # Floor 2  
            'pm_003': {'min': 30, 'max': 85, 'name': 'Main_Building'}, # Main building
            'pm_004': {'min': 20, 'max': 80, 'name': 'Chiller'},      # Chiller (highest)
            'pm_005': {'min': 2, 'max': 8, 'name': 'Elevator'}        # Elevator
        }
        
    async def connect_db(self):
        """Connect to TimescaleDB"""
        try:
            self.connection = await asyncpg.connect(**DB_CONFIG)
            print("✅ Connected to TimescaleDB")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
        return True
    
    async def clear_existing_data(self):
        """Clear existing sensor data for fresh demo"""
        try:
            result = await self.connection.execute("DELETE FROM sensor_data")
            print(f"✅ Cleared existing sensor data")
        except Exception as e:
            print(f"❌ Failed to clear data: {e}")
    
    def get_occupancy_factor(self, timestamp, zone_type, zone_id):
        """Calculate realistic occupancy factor based on time and zone type"""
        hour = timestamp.hour
        weekday = timestamp.weekday()  # 0=Monday, 6=Sunday
        
        # Base occupancy patterns
        if zone_type == 'public':  # Lobby
            if 8 <= hour <= 18:
                base = 0.6
            elif 6 <= hour <= 22:
                base = 0.4
            else:
                base = 0.1
                
        elif zone_type == 'meeting':  # Conference room
            # Meeting spikes at 10AM (as requested)
            if hour == 10:
                base = 0.9  # High occupancy meeting
            elif hour in [14, 16]:  # Afternoon meetings
                base = 0.7
            elif 9 <= hour <= 17:
                base = 0.2  # Light usage
            else:
                base = 0.0
                
        elif zone_type == 'dining':  # Restaurant
            if hour in [12, 13]:  # Lunch peak
                base = 0.8
            elif hour in [18, 19]:  # Dinner peak
                base = 0.6
            elif 11 <= hour <= 14 or 17 <= hour <= 21:
                base = 0.4
            else:
                base = 0.1
                
        elif zone_type == 'office':  # Traditional office
            if weekday >= 5:  # Weekend
                base = 0.1
            elif 9 <= hour <= 17:
                base = 0.7
            elif hour in [8, 18]:
                base = 0.4
            else:
                base = 0.05
                
        elif zone_type == 'flexible':  # Co-working
            if weekday >= 5:  # Weekend
                base = 0.3
            elif 9 <= hour <= 17:
                base = 0.6
            elif 19 <= hour <= 21:  # Evening workers
                base = 0.3
            else:
                base = 0.1
        else:
            base = 0.3
            
        # Add some randomness
        variation = random.uniform(0.8, 1.2)
        return min(1.0, base * variation)
    
    def generate_iaq_values(self, occupancy_factor, zone_type, hours_ago):
        """Generate realistic IAQ values based on occupancy"""
        
        # Base environmental conditions
        base_co2 = 420  # Outdoor CO2
        base_temp = 22.0  # Target temperature
        base_humidity = 45  # Target humidity
        
        # Occupancy impact on CO2 (higher occupancy = higher CO2)
        co2_increase = occupancy_factor * random.uniform(200, 400)
        co2 = base_co2 + co2_increase
        
        # Add some random variation
        co2 += random.uniform(-50, 50)
        
        # Temperature varies with occupancy and time
        temp_variation = occupancy_factor * random.uniform(0.5, 2.0)
        temperature = base_temp + temp_variation + random.uniform(-1.0, 1.0)
        
        # Humidity varies with occupancy
        humidity_variation = occupancy_factor * random.uniform(5, 15)
        humidity = base_humidity + humidity_variation + random.uniform(-5, 5)
        
        # Add equipment degradation pattern for Zone 2_3 (for predictive maintenance demo)
        if zone_type == 'office' and hours_ago < 24:  # Last 24 hours
            # Simulate gradual temperature control degradation
            degradation_factor = (24 - hours_ago) / 24 * 0.1  # Gradual increase
            temperature += degradation_factor * 2  # Getting warmer (AC struggling)
            co2 += degradation_factor * 100  # Ventilation struggling
        
        # Ensure realistic ranges
        co2 = max(380, min(2000, co2))
        temperature = max(18, min(28, temperature))
        humidity = max(25, min(75, humidity))
        
        return round(co2), round(temperature, 1), round(humidity, 1)
    
    def generate_power_values(self, timestamp, meter_id, hours_ago):
        """Generate realistic power consumption patterns"""
        hour = timestamp.hour
        weekday = timestamp.weekday()
        
        meter_info = self.power_ranges[meter_id]
        min_power = meter_info['min']
        max_power = meter_info['max']
        
        # Base load factor based on time and day
        if meter_id == 'pm_004':  # Chiller - weather dependent
            # Higher consumption during day, varies with outside temperature
            if 10 <= hour <= 18:
                base_factor = 0.7 + random.uniform(0, 0.3)  # High cooling load
            elif 6 <= hour <= 22:
                base_factor = 0.5 + random.uniform(0, 0.2)
            else:
                base_factor = 0.3 + random.uniform(0, 0.1)  # Night setback
                
        elif meter_id == 'pm_005':  # Elevator - occupancy dependent
            if weekday >= 5:  # Weekend
                base_factor = 0.2
            elif 8 <= hour <= 18:
                base_factor = 0.6 + random.uniform(0, 0.4)  # Busy periods
            else:
                base_factor = 0.1 + random.uniform(0, 0.1)
                
        else:  # Floor meters - occupancy dependent
            if weekday >= 5:  # Weekend
                base_factor = 0.3
            elif 9 <= hour <= 17:
                base_factor = 0.6 + random.uniform(0, 0.3)  # Business hours
            elif hour in [8, 18]:
                base_factor = 0.5 + random.uniform(0, 0.2)  # Transition
            else:
                base_factor = 0.2 + random.uniform(0, 0.1)  # After hours
        
        # Calculate power consumption
        power = min_power + (max_power - min_power) * base_factor
        
        # Add equipment degradation for pm_002 (Floor 2) - for predictive maintenance demo
        if meter_id == 'pm_002' and hours_ago <= 72:  # Last 3 days
            # Gradual efficiency loss (15% over 3 days)
            degradation = (72 - hours_ago) / 72 * 0.15
            power *= (1 + degradation)
        
        # Add random variation
        power += random.uniform(-2, 2)
        
        return round(power, 2)
    
    async def generate_sensor_data(self):
        """Generate 3 days of historical sensor data"""
        print("🔄 Generating 3 days of historical building data...")
        
        data_points = []
        now = datetime.now()
        
        # Generate hourly data for last 72 hours (3 days)
        for hours_ago in range(72, 0, -1):
            timestamp = now - timedelta(hours=hours_ago)
            
            # Generate IAQ data for all 10 zones
            for zone_id, zone_info in self.zones.items():
                zone_type = zone_info['type']
                occupancy = self.get_occupancy_factor(timestamp, zone_type, zone_id)
                
                co2, temp, humidity = self.generate_iaq_values(occupancy, zone_type, hours_ago)
                
                # IAQ sensor points (following your BRICK schema)
                sensor_id = zone_id.replace('zone_', 'iaq_')
                
                # CO2, Temperature, Humidity points
                data_points.extend([
                    (timestamp, f"{sensor_id}_co2", co2),
                    (timestamp, f"{sensor_id}_temp", temp), 
                    (timestamp, f"{sensor_id}_humid", humidity)
                ])
            
            # Generate power data for all 5 meters
            for meter_id in self.power_ranges.keys():
                power = self.generate_power_values(timestamp, meter_id, hours_ago)
                data_points.append((timestamp, f"{meter_id}_power", power))
            
            if hours_ago % 24 == 0:
                print(f"  📅 Generated day {int(hours_ago/24)} data")
        
        return data_points
    
    async def insert_data(self, data_points):
        """Insert generated data into TimescaleDB"""
        print(f"💾 Inserting {len(data_points)} data points...")
        
        # Batch insert for performance
        await self.connection.executemany(
            "INSERT INTO sensor_data (timestamp, point_id, value) VALUES ($1, $2, $3)",
            data_points
        )
        
        print(f"✅ Successfully inserted {len(data_points)} data points")
    
    async def verify_data(self):
        """Verify the inserted data"""
        # Check data count
        count = await self.connection.fetchval("SELECT COUNT(*) FROM sensor_data")
        print(f"📊 Total records in database: {count}")
        
        # Check date range
        date_range = await self.connection.fetchrow(
            "SELECT MIN(timestamp) as earliest, MAX(timestamp) as latest FROM sensor_data"
        )
        print(f"📅 Data range: {date_range['earliest']} to {date_range['latest']}")
        
        # Sample some data
        sample = await self.connection.fetch("""
            SELECT point_id, AVG(value) as avg_value, COUNT(*) as count
            FROM sensor_data 
            WHERE point_id LIKE '%co2' OR point_id LIKE '%power'
            GROUP BY point_id 
            ORDER BY point_id
        """)
        
        print("\n📈 Sample averages:")
        for row in sample:
            print(f"  {row['point_id']}: {row['avg_value']:.1f} ({row['count']} readings)")
    
    async def run(self):
        """Main seeding process"""
        print("🌱 Starting Historical Building Data Seeding...")
        print("=" * 50)
        
        # Connect to database
        if not await self.connect_db():
            return
        
        try:
            # Clear existing data
            await self.clear_existing_data()
            
            # Generate new data
            data_points = await self.generate_sensor_data()
            
            # Insert data
            await self.insert_data(data_points)
            
            # Verify data
            await self.verify_data()
            
            print("\n" + "=" * 50)
            print("🎯 Historical data seeding completed successfully!")
            print("📋 Your building now has 3 days of realistic operational data")
            print("🚀 Ready for demo!")
            
        except Exception as e:
            print(f"❌ Seeding failed: {e}")
            
        finally:
            await self.connection.close()

async def main():
    """Run the seeding script"""
    seeder = BuildingDataSeeder()
    await seeder.run()

if __name__ == "__main__":
    # Run the seeding script
    asyncio.run(main())