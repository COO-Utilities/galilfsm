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

dmc30000 = __import__("dmc30000")
DMC30000 = dmc30000.DMC30000


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
        raise dmc30000.gclib.Error("simulated failure")


@pytest.fixture
def controller():
    ctrl = DMC30000(log=False)
    ctrl._client = RecordingClient()
    return ctrl


# Setter -> exact command sent


@pytest.mark.parametrize("channel", dmc30000.ANALOG_OUTPUTS)
def test_set_analog_output_sends_correct_command(controller, channel):
    assert controller.set_analog_output(channel, -3.25) is True
    assert controller._client.commands == [f"AO {channel},-3.25"]


@pytest.mark.parametrize("bad_voltage", [10.0, -10.0, 9.9999, -9.9999])
def test_set_analog_output_rejects_out_of_range_voltage_and_sends_nothing(controller, bad_voltage):
    with pytest.raises(ValueError):
        controller.set_analog_output(1, bad_voltage)
    assert controller._client.commands == []


def test_set_analog_output_accepts_boundary_voltages(controller):
    controller.set_analog_output(1, dmc30000.VOLTAGE_MAX)
    controller.set_analog_output(2, dmc30000.VOLTAGE_MIN)
    assert controller._client.commands == [
        f"AO 1,{dmc30000.VOLTAGE_MAX}",
        f"AO 2,{dmc30000.VOLTAGE_MIN}",
    ]


@pytest.mark.parametrize("bad_channel", [0, 3, -1])
def test_invalid_channel_raises_and_sends_nothing(controller, bad_channel):
    with pytest.raises(ValueError):
        controller.set_analog_output(bad_channel, 1.0)
    with pytest.raises(ValueError):
        controller.get_analog_output(bad_channel)
    assert controller._client.commands == []


def test_set_analog_output_returns_false_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.set_analog_output(1, 1.0) is False


# Getter -> exact command sent + correct parsing


@pytest.mark.parametrize("channel", dmc30000.ANALOG_OUTPUTS)
def test_get_analog_output_sends_correct_query_and_parses_reply(controller, channel):
    controller._client.reply = "-1.1"
    value = controller.get_analog_output(channel)
    assert controller._client.commands == [f"MG@AO[{channel}]"]
    assert value == -1.1


def test_getter_returns_none_on_unparsable_reply(controller):
    controller._client.reply = "not-a-number"
    assert controller.get_analog_output(1) is None
    # command was still sent, it's the reply parsing that failed
    assert controller._client.commands == ["MG@AO[1]"]


def test_getter_returns_none_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.get_analog_output(1) is None
    assert controller._client.commands == ["MG@AO[1]"]


# Initialize


def test_initialize_sends_ao1_setup_in_order(controller):
    assert controller.initialize() is True
    assert controller._client.commands == ["MO A", "MT 1", "BR 0", "BA A"]


def test_initialize_stops_at_first_failure(controller):
    controller._client = FailingClient()
    assert controller.initialize() is False
    assert controller._client.commands == ["MO A"]


# No-client guard rails (both getter and setter route through _send_command)


def test_getter_with_no_client_returns_none_and_sends_nothing():
    ctrl = DMC30000(log=False)
    assert ctrl._client is None
    assert ctrl.get_analog_output(1) is None


def test_setter_with_no_client_does_not_raise():
    ctrl = DMC30000(log=False)
    assert ctrl._client is None
    # validation passes, _send_command just reports failure internally
    assert ctrl.set_analog_output(1, 1.0) is False  # should not raise

def test_cannot_reconnect_if_have_not_ever_connected():
    """reconnect() with no prior connect() call has no client to reopen."""
    ctrl = DMC30000(log=False)
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
    ctrl = DMC30000(log=False)
    assert ctrl._send_command("MG@AO[1]") is False
