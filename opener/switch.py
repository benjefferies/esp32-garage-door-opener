"""
Switch controller for the garage door opener
"""

from machine import Pin
from settings import MOSFET_PIN, GARAGE_DOOR_PULSE_MS
import time

class SwitchController:
    def __init__(self, is_cold_boot=False):
        self.is_cold_boot = is_cold_boot
        self.led = None
        self.switch = None
        self.initialize()
    
    def initialize(self):
        """Initialize the hardware"""
        # Initialize LED
        self.led = Pin(MOSFET_PIN, Pin.OUT, value=0)
        if self.is_cold_boot:
            print(f"LED initialized on GPIO {MOSFET_PIN}")
        
        # Initialize garage door switch
        self.switch = Pin(MOSFET_PIN, Pin.OUT, value=0)
        if self.is_cold_boot:
            print(f"Switch initialized on GPIO {MOSFET_PIN}")
    
    def toggle(self):
        """
        Toggle both the LED and the switch
        The garage door opener typically requires a momentary contact
        """
        if not self.led or not self.switch:
            return False
            
        # Toggle LED
        self.led.value(not self.led.value())
        
        # Pulse the switch
        self.switch.value(1)
        time.sleep_ms(GARAGE_DOOR_PULSE_MS)
        self.switch.value(0)
        
        return True
    
    def get_state(self):
        """Get current LED state"""
        return self.led.value() if self.led else 0
    
    def cleanup(self):
        """Clean up resources"""
        if self.led:
            self.led.value(0)  # Ensure LED is off
            self.led = None
        if self.switch:
            self.switch.value(0)  # Ensure switch is off
            self.switch = None 