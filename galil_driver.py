# pyright: reportImplicitOverride=false
from __future__ import annotations

from typing import NamedTuple, Self, override

import gclib  # pyright: ignore[reportMissingImports]  # Linux and Windows only, requires Galil software
from hardware_device_base import HardwareDeviceBase

VOLTAGE_MAX = 9.9998
VOLTAGE_MIN = -9.9998

class _Axis(NamedTuple):
    label: str
    get_command: str
    set_command: str  # add voltage to end of string when using


X_AXIS = _Axis(label="X+", get_command="MG@AO[1]", set_command="AO 1,")
Y_AXIS = _Axis(label="Y+", get_command="MG@AO[2]", set_command="AO 2,")


class GalilDeviceController(HardwareDeviceBase):
    """Facilitates Communication between Galil (DMC-30014) and Fast Steering Mirror (FSM)"""

    def __init__(
        self, log: bool = True, logfile: str = __name__.rsplit(".", 1)[-1]
    ) -> None:
        super().__init__(log, logfile)
        self._ipaddr: str | None = None
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
        if self.is_connected() == True:
            self.report_error("Controller is connected. Disconnect before trying to reconnnect")
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

    def _send_voltage(self, axis: _Axis, voltage: float) -> bool:
        """Sends Voltage to FSM controller for given axis and reports success in logs"""
        success = self._send_command(f"{axis.set_command}{voltage}")
        if success:
            self.report_info(
                f"Successfully sent {voltage} volts to {axis.label} command on FSM Controller"
            )
        else:
            self.report_info("Failed to send voltage to FSM Controller")
        return success

    def _get_voltage(self, axis: _Axis) -> float | None:
        """Gets voltage from FSM controller for the specified axis"""
        if self._send_command(axis.get_command):
            reply = self._read_reply()
            try:
                return float(reply) if reply is not None else None
            except ValueError:
                self.report_error(f"Unexpected reply for {axis.label} axis: {reply!r}")
                return None
        self.report_error("Command failed")
        return None

    @property
    def x_voltage(self) -> float | None:
        """Sends command to galil to get x_voltage"""
        return self._get_voltage(X_AXIS)

    @x_voltage.setter
    def x_voltage(self, voltage: float) -> None:
        """Sets x voltage and sends it to FSM Controller"""
        self._validate_voltage(voltage)
        self._send_voltage(X_AXIS, voltage)

    @property
    def y_voltage(self) -> float | None:
        """Sends command to galil to get y_voltage"""
        return self._get_voltage(Y_AXIS)

    @y_voltage.setter
    def y_voltage(self, voltage: float) -> None:
        """Sets y voltage and sends it to FSM Controller"""
        self._validate_voltage(voltage)
        self._send_voltage(Y_AXIS, voltage)

    def send_position_voltage(self, x_volt: float = 0, y_volt: float = 0) -> None:
        """Sends analog voltages to set FSM position sequencially. X then Y."""
        # FIX: should do these concurrently
        self.x_voltage = x_volt
        self.y_voltage = y_volt

    @override
    def initialize(self) -> bool:
        """initialize motor and Axis so Analog can be sent for both directions"""
        # NOTE: This should eventually be fazed out and coded into the galil using #AUTO so it does this on startup
        if self._client is None:
            self.report_error("Client controller has not been defined")
            return False

        init_commands = ("MO A", "MT 1", "BR 0", "BA A")

        for command in init_commands:
            success = self._send_command(command)
            if not success:
                self.report_error(f"Initialization failed at command: {command}")
                return False

        self.report_info("Controller ready to operate")
        return True

    @property
    def ipaddr(self) -> str | None:
        """IP address of the currently connected Galil, if any."""
        return self._ipaddr

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()


# MT must be set for servo or 2PB motor and BA is set for A access, MT can't be changed when sending analog output
# to set MT, the motor must be off MO
# for DMC-30014 the amplifier is a linear sine drive
# must set MT 1 or -1
# then BA A
# for general purpose analog output MT 1 or -1, BR 0
