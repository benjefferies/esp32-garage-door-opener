"""
Button handling for the ESP32-NOW Gateway
"""

from machine import Pin
from utils import log
from config import BUTTON_PIN, DEBOUNCE_DELAY, LOOP_DELAY
from message_manager import MessageManager
import time

class ButtonHandler:
    def __init__(self, message_manager: MessageManager):
        """
        Initialize the button handler.
        
        Args:
            message_manager: The message manager for async sending
        """
        self.button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        self.message_manager = message_manager
        self.last_button_state = self.button.value()
        log(f"Button initialized on GPIO {BUTTON_PIN}")
    
    def handle_button(self) -> None:
        """
        Handle button state changes and queue toggle commands when pressed.
        This is non-blocking - messages are sent async.
        """
        button_state = self.button.value()
        
        if button_state != self.last_button_state:
            log(f"Button state changed from {self.last_button_state} to {button_state}")
            
            if button_state == 0:  # Button pressed
                self.message_manager.send_toggle_async()
            
            self.last_button_state = button_state
            time.sleep(DEBOUNCE_DELAY)
        
        time.sleep(LOOP_DELAY) 