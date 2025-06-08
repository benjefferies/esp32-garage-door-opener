# ESP32 Garage Door Opener Gateway

This is the sender/gateway implementation for the ESP32 garage door opener system. It uses ESP-NOW to send commands to the garage door opener receiver.

## Hardware Requirements

- ESP32 development board (any model)
- The built-in BOOT button (GPIO 0) is used as the trigger

## Setup

1. Flash this code to your ESP32 gateway device
2. Make sure the receiver (opener) is powered on and running its code
3. Press the BOOT button to send a toggle command to the garage door opener

## How it Works

- The gateway uses ESP-NOW to send broadcast messages
- When the button is pressed, it sends a 'toggle' command
- The receiver will receive this command and toggle the garage door state

## Troubleshooting

- If the garage door doesn't respond, check that both devices are powered on
- Make sure both devices are within range of each other
- Verify that the receiver's code is running correctly
- Check the serial monitor for any error messages 