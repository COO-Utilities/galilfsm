# pyright: reportImplicitOverride=false
from __future__ import annotations

from typing import Self, override

import gclib  # pyright: ignore[reportMissingImports]  # Linux and Windows only, requires Galil software
from hardware_device_base import HardwareDeviceBase

VOLTAGE_MAX = 10 # I think it is actually 9.9998
VOLTAGE_MIN = -10 # I think it is actually -9.9998

X_COMMAND = "AO 1"
Y_COMMAND = "AO 2"


class GalilDeviceController(HardwareDeviceBase):
    """Facilitates Communication between Galil (DMC-30014) and Fast Steering Mirror (FSM)"""

    def __init__(
        self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1]
    ) -> None:
        super().__init__(log, logfile)
        self.ipaddr: str | None = None
        self._client: gclib.Controller | None = None
        self._last_reply: str | None = None

    @override
    def connect(self, ipaddr: str, baud_rate: int | None = None) -> None:
        """
        Creates a Controller for the FSM. This creates a connection to the galil.

        :param str ipaddr: ip address of the Galil
        :param int baud_rate: Baud rate of the Galil (only required for serial connection)
        """
        if self.is_connected():
            self.disconnect()

        self.report_info(f"Connecting to Galil at IP Address: {ipaddr}...")
        try:
            self._client = (
                gclib.Controller(ipaddr, baud_rate)
                if baud_rate
                else gclib.Controller(ipaddr)
            )
        except gclib.Error as e:
            self.report_error(f"Could not connect to Galil at {ipaddr}: {e}")

        self.ipaddr = ipaddr
        self._set_connected(True)
        self.report_info(f"Successfully connected to Galil at {ipaddr}")

    @override
    def disconnect(self) -> None:
        """Disconnects Controller from Galil"""
        if self._client == None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return

        try:
            self.report_info(f"Disconnecting Galil at {self.ipaddr}")
            self._client.close()
            self._set_connected(False)
            self.report_info("Closed connection")
        except gclib.Error as e:
            self.report_error(f"Failed to disconnect: {e}")

    def reconnect(self) -> bool:
        """Reconnects controller. Only works if used disconnect in the past"""
        if self._client == None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return False

        try:
            self.report_info(f"Connecting to galil at {self.ipaddr}...")
            self._client.open()
            self._set_connected(True)
            self.report_info(f"Connected Controller at {self.ipaddr}")
            return True
        except gclib.Error as e:
            self.report_error(f"Failed to reconnect: {e}")

        return False

    @override
    def _send_command(self, command: str) -> bool:
        """
        Sends a command to Galil and return if command was successfully sent

        :param str command: command to send over
        """
        if self._client == None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return False

        try:
            self._last_reply = self._client.command(command)
            self.report_info(f"Command: {command} successfully sent")
            return True
        except gclib.Error as e:
            self._last_reply = None
            self.report_error(f"Command {command} failed: {e}")

        return False

    @override
    def _read_reply(self) -> str | None:
        """Returns the last reply from the last command"""
        return self._last_reply

    def _send_output_voltage(self, command: str, voltage: float = 0) -> None:
        """
        Sends a analog voltage to the FSM (either to X or Y)
        Voltage needs to be between -9.9998 and 9.9998
        """
        axis = "X+" if command == X_COMMAND else "Y+"
        self.report_info(f"Sending {voltage} volts to {axis} command on FSM Controller...")

        if voltage > VOLTAGE_MAX and voltage < VOLTAGE_MIN:
            self.report_error(f"Voltage needs to be between {VOLTAGE_MIN} and {VOLTAGE_MAX}.")
            return
        # send Analog Output command and capture success
        success = self._send_command(f"{command},{voltage}")
        if success:
            self.report_info(f"Successfully sent {voltage} volts to {axis} command on FSM Controller")
        else:
            self.report_info("Failed to send voltage to FSM Controller")

    def set_x_voltage(self, voltage: float = 0) -> None:
        """
        Sends an analog voltage to FSM to set X position
        Voltage needs to be between -9.9998 and 9.9998
        """
        self._send_output_voltage(X_COMMAND, voltage)

    def set_y_voltage(self, voltage: float = 0) -> None:
        """
        Sends an analog voltage to FSM to set Y position
        Voltage needs to be between -9.9998 and 9.9998
        """
        self._send_output_voltage(Y_COMMAND, voltage)

    def set_position_voltage(self, x_volt: float = 0, y_volt: float = 0) -> None:
        """
        Sends an analog voltage to FSM to set position
        starts with X then does Y
        """
        # FIX: should do these concurrently
        self._send_output_voltage(X_COMMAND, x_volt)
        self._send_output_voltage(Y_COMMAND, y_volt)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_:object) -> None:
        self.disconnect()
