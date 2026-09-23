# pyright: reportImplicitOverride=false
"""Driver for the Galil DMC-30000 series (single-axis) motion controller."""
from __future__ import annotations

from typing import Self, override

import gclib  # pyright: ignore[reportMissingImports]  # Linux and Windows only, requires Galil software
from hardware_device_base import HardwareDeviceBase

# AO1 and AO2 are +/-10V, 16-bit DACs. Clamp to the largest value the DAC can represent.
VOLTAGE_MAX = 9.9998
VOLTAGE_MIN = -9.9998

# AO1 is the axis A motor command line; it only works as a general analog output
# after initialize(). AO2 is always a general analog output.
ANALOG_OUTPUTS = (1, 2)


class DMC30000(HardwareDeviceBase):
    """Controls a Galil DMC-30000 series controller over gclib"""

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
        Opens a gclib connection to the Galil.

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
        if self._client is None:
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
        if self._client is None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return False
        if self.is_connected():
            self.report_error("Controller is connected. Disconnect before trying to reconnect")
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
        if self._client is None:
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
    def _validate_channel(channel: int) -> None:
        if channel not in ANALOG_OUTPUTS:
            raise ValueError(
                f"Analog output {channel} does not exist, must be one of {ANALOG_OUTPUTS}"
            )

    @staticmethod
    def _validate_voltage(voltage: float) -> None:
        if not (VOLTAGE_MIN <= voltage <= VOLTAGE_MAX):
            raise ValueError(
                f"Voltage {voltage} out of range [{VOLTAGE_MIN}, {VOLTAGE_MAX}]"
            )

    def set_analog_output(self, channel: int, voltage: float) -> bool:
        """
        Sets an analog output to the given voltage and returns if it was successfully sent

        :param int channel: analog output number (1 or 2)
        :param float voltage: voltage between VOLTAGE_MIN and VOLTAGE_MAX
        """
        self._validate_channel(channel)
        self._validate_voltage(voltage)
        success = self._send_command(f"AO {channel},{voltage}")
        if success:
            self.report_info(f"Set AO{channel} to {voltage} volts")
        else:
            self.report_error(f"Failed to set AO{channel}")
        return success

    def get_analog_output(self, channel: int) -> float | None:
        """
        Returns the voltage currently output by the Galil on an analog output

        :param int channel: analog output number (1 or 2)
        """
        self._validate_channel(channel)
        if self._send_command(f"MG@AO[{channel}]"):
            reply = self._read_reply()
            try:
                return float(reply) if reply is not None else None
            except ValueError:
                self.report_error(f"Unexpected reply for AO{channel}: {reply!r}")
                return None
        self.report_error("Command failed")
        return None

    @override
    def initialize(self) -> bool:
        """Configures axis A so AO1 can be used as a general analog output"""
        # NOTE: This should eventually be fazed out and coded into the galil using #AUTO so it does this on startup
        if self._client is None:
            self.report_error("Client controller has not been defined")
            return False

        # MT can only be changed with the motor off (MO). For AO1 to act as a general
        # analog output MT must be 1 or -1, BR 0, and BA set for axis A.
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
