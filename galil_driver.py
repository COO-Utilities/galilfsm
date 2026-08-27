# pyright: reportImplicitOverride=false

from __future__ import annotations

from typing import override

import gclib  # pyright: ignore[reportMissingImports]  # Linux and Windows only, requires Galil software
from hardware_device_base import HardwareDeviceBase

# NOTE: should have a dataclass or something of all the different commands that can be issued

# IA is the command to get ip address

class GalilMotionController(HardwareDeviceBase):
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
            self._set_connected(True)
        except gclib.Error as e:
            self.report_error(f"{e}")

    @override
    def disconnect(self) -> None:
        """Disconnects Controller from Galil"""
        if self._client == None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return

        try:
            # FIX: say disconnecting from serial port or not
            self.report_info("Disconnecting Galil")
            self._client.close()
            self._set_connected(False)
        except gclib.Error as e:
            self.report_error(f"{e}")

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
            self.report_error(f"{e}")

        return False

    @override
    def _read_reply(self) -> str | None:
        """Returns the last reply from the last command"""
        return self._last_reply

    # def get_data_record(self, timeout: int = -1) -> gclib.DataRecord | None:
    #     if self._client == None:
    #         return
    #     self._client.data_record(timeout=timeout)
