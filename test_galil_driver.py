import sys
import types

import pytest

# Stub out external dependencies before importing the module under test


def _install_fake_gclib() -> None:
    fake_gclib = types.ModuleType("gclib")

    class Error(Exception):
        pass

    class Controller:
        def __init__(self, ipaddr, baud_rate=None):
            self.ipaddr = ipaddr
            self.baud_rate = baud_rate

        def command(self, cmd):
            return ""

        def close(self):
            pass

        def open(self):
            pass

    fake_gclib.Error = Error
    fake_gclib.Controller = Controller
    sys.modules["gclib"] = fake_gclib


def _install_fake_hardware_base() -> None:
    fake_module = types.ModuleType("hardware_device_base")

    class HardwareDeviceBase:
        def __init__(self, log=True, logfile=""):
            self._log = log
            self._logfile = logfile
            self._connected = False

        def report_info(self, msg):
            pass

        def report_error(self, msg):
            pass

        def _set_connected(self, value):
            self._connected = value

        def is_connected(self):
            return self._connected

    fake_module.HardwareDeviceBase = HardwareDeviceBase
    sys.modules["hardware_device_base"] = fake_module


_install_fake_gclib()
_install_fake_hardware_base()

galil_controller = __import__("galil_driver")
GalilDeviceController = galil_controller.GalilDeviceController


# Helpers
class RecordingClient:
    """Fake gclib.Controller that records every command string it receives."""

    def __init__(self, reply: str = "1.2345"):
        self.commands: list[str] = []
        self.reply = reply

    def command(self, cmd: str) -> str:
        self.commands.append(cmd)
        return self.reply

    def close(self):
        pass

    def open(self):
        pass


class FailingClient(RecordingClient):
    """Fake client whose command() always raises, to test failure paths."""

    def command(self, cmd: str) -> str:
        self.commands.append(cmd)
        raise galil_controller.gclib.Error("simulated failure")


@pytest.fixture
def controller():
    ctrl = GalilDeviceController(log=False)
    ctrl._client = RecordingClient()
    return ctrl


# Setter -> exact command sent


def test_x_voltage_setter_sends_correct_command(controller):
    controller.x_voltage = 5.0
    assert controller._client.commands == ["AO 1,5.0"]


def test_y_voltage_setter_sends_correct_command(controller):
    controller.y_voltage = -3.25
    assert controller._client.commands == ["AO 2,-3.25"]


def test_send_position_voltage_sends_x_then_y_in_order(controller):
    controller.send_position_voltage(x_volt=1.0, y_volt=2.0)
    assert controller._client.commands == ["AO 1,1.0", "AO 2,2.0"]


def test_send_position_voltage_defaults_to_zero(controller):
    controller.send_position_voltage()
    assert controller._client.commands == ["AO 1,0", "AO 2,0"]


@pytest.mark.parametrize("bad_voltage", [10.0, -10.0, 9.9999, -9.9999])
def test_setter_rejects_out_of_range_voltage_and_sends_nothing(controller, bad_voltage):
    with pytest.raises(ValueError):
        controller.x_voltage = bad_voltage
    assert controller._client.commands == []


def test_setter_accepts_boundary_voltages(controller):
    controller.x_voltage = galil_controller.VOLTAGE_MAX
    controller.y_voltage = galil_controller.VOLTAGE_MIN
    assert controller._client.commands == [
        f"AO 1,{galil_controller.VOLTAGE_MAX}",
        f"AO 2,{galil_controller.VOLTAGE_MIN}",
    ]


# Getter -> exact command sent + correct parsing


def test_x_voltage_getter_sends_correct_query_and_parses_reply(controller):
    controller._client.reply = "4.5"
    value = controller.x_voltage
    assert controller._client.commands == ["MG@AO[1]"]
    assert value == 4.5


def test_y_voltage_getter_sends_correct_query_and_parses_reply(controller):
    controller._client.reply = "-1.1"
    value = controller.y_voltage
    assert controller._client.commands == ["MG@AO[2]"]
    assert value == -1.1


def test_getter_returns_none_on_unparsable_reply(controller):
    controller._client.reply = "not-a-number"
    assert controller.x_voltage is None
    # command was still sent, it's the reply parsing that failed
    assert controller._client.commands == ["MG@AO[1]"]


def test_getter_returns_none_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.x_voltage is None
    assert controller._client.commands == ["MG@AO[1]"]


# No-client guard rails (both getter and setter route through _send_command)


def test_getter_with_no_client_returns_none_and_sends_nothing():
    ctrl = GalilDeviceController(log=False)
    assert ctrl._client is None
    assert ctrl.x_voltage is None


def test_setter_with_no_client_does_not_raise():
    ctrl = GalilDeviceController(log=False)
    assert ctrl._client is None
    # validation passes, _send_command just reports failure internally
    ctrl.x_voltage = 1.0  # should not raise

def test_cannot_reconnect_if_have_not_ever_connected():
    """reconnect() with no prior connect() call has no client to reopen."""
    ctrl = GalilDeviceController(log=False)
    assert ctrl._client is None

    result = ctrl.reconnect()

    assert result is False
    assert ctrl.is_connected() is False


def test_cannot_reconnect_before_disconnect(controller):
    """reconnect() while still connected should not silently succeed."""
    controller._set_connected(True)

    result = controller.reconnect()

    assert result is False


def test_send_command_returns_false_if_not_connected():
    """_send_command() with no client (never connected) must return False."""
    ctrl = GalilDeviceController(log=False)
    assert ctrl._send_command("MG@AO[1]") is False
