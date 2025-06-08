"""
Button handling for the ESP32-NOW Gateway
"""

from machine import Pin
from utils import log
from config import BUTTON_PIN, DEBOUNCE_DELAY, LOOP_DELAY
from network_manager import send_toggle_with_ack
import time

class ButtonHandler:
    def __init__(self, espnow_instance):
        """
        Initialize the button handler.
        
        Args:
            espnow_instance: The ESP-NOW instance for sending commands
        """
        self.button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        self.espnow_instance = espnow_instance
        self.last_button_state = self.button.value()
        self.message_id = 0
        log(f"Button initialized on GPIO {BUTTON_PIN}")
    
    def handle_button(self) -> None:
        """
        Handle button state changes and send toggle commands when pressed.
        """
        button_state = self.button.value()
        
        if button_state != self.last_button_state:
            log(f"Button state changed from {self.last_button_state} to {button_state}")
            
            if button_state == 0:  # Button pressed
                self.message_id += 1
                send_toggle_with_ack(self.espnow_instance, self.message_id)
            
            self.last_button_state = button_state
            time.sleep(DEBOUNCE_DELAY)
        
        time.sleep(LOOP_DELAY) 