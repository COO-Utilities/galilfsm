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
        self._ipaddr: str | None = None
        self._client: gclib.Controller | None = None
        self._last_reply: str | None = None
        self._x_voltage: float = 0.0
        self._y_voltage: float = 0.0

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
            return

        self._ipaddr = ipaddr
        self._set_connected(True)
        self.report_info(f"Successfully connected to Galil at {ipaddr}")

    @override
    def disconnect(self) -> None:
        """Disconnects Controller from Galil"""
        if self._client == None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return

        try:
            self.report_info(f"Disconnecting Galil at {self._ipaddr}")
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
            self.report_info(f"Connecting to galil at {self._ipaddr}...")
            self._client.open()
            self._set_connected(True)
            self.report_info(f"Connected Controller at {self._ipaddr}")
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

    @staticmethod
    def _validate_voltage(voltage: float) -> None:
        if not (VOLTAGE_MIN <= voltage <= VOLTAGE_MAX):
            raise ValueError(
                f"Voltage {voltage} out of range [{VOLTAGE_MIN}, {VOLTAGE_MAX}]"
            )

    def _send_voltage(self, command: str, axis_label: str, voltage: float) -> bool:
        """Sends Voltage to FSM controller and reports success in logs"""
        success = self._send_command(f"{command},{voltage}")
        if success:
            self.report_info(f"Successfully sent {voltage} volts to {axis_label} command on FSM Controller")
        else:
            self.report_info("Failed to send voltage to FSM Controller")
        return success

    @property
    def x_voltage(self) -> float:
        """Last commanded X-axis voltage. This is not necessarily the X-axis Voltage of the FMS"""
        return self._x_voltage

    @x_voltage.setter
    def x_voltage(self, voltage: float) -> None:
        """Sets x voltage and sends it to FSM Controller"""
        self._validate_voltage(voltage)
        if self._send_voltage(X_COMMAND, "X+", voltage):
            self._x_voltage = voltage

    @property
    def y_voltage(self) -> float:
        """Last commanded Y-axis voltage. This is not necessarily the Y-axis Voltage of the FMS"""
        return self._y_voltage

    @y_voltage.setter
    def y_voltage(self, voltage: float) -> None:
        """Sets y voltage and sends it to FSM Controller"""
        self._validate_voltage(voltage)
        if self._send_voltage(Y_COMMAND, "Y+", voltage):
            self._y_voltage = voltage

    def send_position_voltage(self, x_volt: float = 0, y_volt: float = 0) -> None:
        """Sends analog voltages to set FSM position. X then Y."""
        # FIX: should do these concurrently
        self.x_voltage = x_volt
        self.y_voltage = y_volt

    @override
    def initialize(self) -> bool:
        """initialize motor and Axis so Analog can be sent for both directions"""
        if self._client is None:
            self.report_error("Client controller has not been defined")
            return False
        self._send_command("MO A")
        self._send_command("MT 1")
        self._send_command("BR 0")
        self._send_command("BA A")
        self._send_command("SH A")
        self.report_info("Controller ready to operate")

        return True

    @property
    def ipaddr(self) -> str | None:
        """IP address of the currently connected Galil, if any."""
        return self._ipaddr

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_:object) -> None:
        self.disconnect()


# MT must be set for servo or 2PB motor and BA is set for A access, MT can't be changed when sending analog output
# to set MT, the motor must be off MO
# for DMC-30014 the amplifier is a linear sine drive
# must set MT 1 or -1
# then BA A


# for general purpose analog output MT 1 or -1, BR 0
