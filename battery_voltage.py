# !/usr/bin/env python
# coding: Latin-1
"""function to print current battery voltage"""
import piconzero
import time

pz = piconzero
pz.init()
time.sleep(0.5)
BATT_CONSTANTS = {
    "adc_gain": 0.02909,
    "adc_offset": -15.06,
    "adc_pin": 3,
    "min_v": 7.45
}
pz.setInputConfig(BATT_CONSTANTS['adc_pin'], 1)
time.sleep(0.01)

def current_batt_v():
    """uses an ADC channel to read battery voltage"""
    voltage_at_pin = float(pz.readInput(BATT_CONSTANTS['adc_pin']))
    return BATT_CONSTANTS['adc_gain'] * voltage_at_pin + BATT_CONSTANTS['adc_offset']

print current_batt_v()

