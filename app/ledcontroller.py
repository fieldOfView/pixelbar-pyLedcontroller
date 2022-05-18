#!/usr/bin/env python3

try:
    import serial
except ModuleNotFoundError:
    pass
import argparse
from app import state
from typing import List, Optional


class LedController:
    GROUP_COUNT = 4  # the number of LED groups defined by the STM32 controller

    def __init__(self) -> None:
        self._device = "/dev/tty.usbserial"  # default device
        self._baudrate = 9600  # default baudrate

        # the state that was most recently sent to the controller, provided that the class instance stays alive
        # defaults to 4x full bright because that's what the controller does when it is powered on
        self._state = state.GroupState()

        try:
            self._serial = serial.Serial(write_timeout=5)
        except NameError:
            print(
                "pySerial module is not installed, so there is no connection with the controller. Try installing it with `python3 -m pip install pyserial`."
            )
            self._serial = None

    def setSerialOptions(self, device: Optional[str], baudrate: Optional[int]) -> None:
        if not self._serial:  # in case pyserial is not available
            return

        if self._serial.is_open:
            raise Exception("serial device is already open")

        if device:
            self._device = device
        if baudrate:
            self._baudrate = baudrate

    def openDevice(self) -> None:
        if not self._serial:  # in case pyserial is not available
            return

        self._serial.port = self._device
        self._serial.baud = self._baudrate
        self._serial.open()  # this may throw its own exception if there's an error opening the device

    def closeDevice(self) -> None:
        if not self._serial:  # in case pyserial is not available
            return

        if self._serial.is_open:
            self._serial.close()

    def setState(self, state: List[bytes]) -> None:
        if len(state) != self.GROUP_COUNT or not all([len(v) == 4 for v in state]):
            raise ValueError("new state is invalidly defined")

        if self._serial and not self._serial.is_open:
            self.openDevice()

        self._state.set_all_groups(state)

        if self._serial:
            # this may throw its own exception if there's an error writing to the serial device
            self._serial.write(self._state.send_format())

    def getState(self) -> List[bytes]:
        return self._state.get_all_states()

    def getHexState(self) -> List[str]:
        return self._state.get_hex_states()

    def parseHexColor(self, hex_color: str) -> bytes:
        hex_bytes = bytes.fromhex(hex_color)
        hex_length = len(hex_bytes)
        if hex_length == 1:
            # RGB and W all equal value
            # input: 0x88 output: 0x88888888
            hex_bytes = hex_bytes * 4
        elif hex_length == 2:
            # RGB all equal, W separate value
            # input: 0x8844 output: 0x88888840
            hex_bytes = hex_bytes[0:1] * 3 + hex_bytes[1:2]
        elif hex_length == 3:
            # RGB only, turn off W
            # input: 0x884422 output: 0x88442200
            hex_bytes = hex_bytes + b"\x00"
        elif hex_length == 4:
            # RGBW as is
            # input: 0x88442211 output: 0x88442211
            pass
        else:
            raise ValueError("only 4 hex bytes are expected per value")

        return hex_bytes

    def stateFromHexColors(self, hex_colors: List[str]) -> List[bytes]:
        if len(hex_colors) == 1:
            # use same value for all groups
            hex_colors = hex_colors * self.GROUP_COUNT
        if len(hex_colors) != self.GROUP_COUNT:
            raise ValueError("only %d or 1 values may be specified" % self.GROUP_COUNT)

        return [self.parseHexColor(value) for value in hex_colors]

    def stateToHexColors(self, state: List[bytes]) -> List[str]:
        return [value.hex() for value in state]
