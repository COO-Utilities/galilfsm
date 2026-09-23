Python driver for the Galil DMC-30000 series (single-axis) controller, e.g. the DMC-30014.

The driver exposes the controller's two analog outputs (AO1, AO2, +/-10V, 16-bit) and knows
nothing about what is wired to them; mapping outputs to a device (e.g. the FSM's X/Y axes) is
the job of the higher-level code.

Manuals: [datasheet](https://www.a2v.fr/galil/doc/cartes/dmc-3x01x/ds_3x01x.pdf),
[user manual](https://www.a2v.fr/galil/doc/cartes/dmc-3x01x/man_3x01x.pdf)

for this to work you need to have gclib installed on your machine
you can do this on Windows or Linux but on macos you have to do some shenanigins (rosetta 2)

## Installing Galil gclib on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install --upgrade --index-url https://www.galil.com/sw/pub/python gclib
```

check version

```python
import gclib
gclib.version()
# should show 2.5.0
```


## Userflow
Enter python shell with `python`

#### Assign IP Address to Galil (If Applicable)
```python
import gclib
gclib.ip_requests()
gclib.addresses()
# find address you want
# define variables mac_address and ip_addr or just input directly
# ip address should be same subnet as host computer
gclib.assign_ip(f'{mac_address}', f'{ip_addr}')
```
#### Connect Controller
```python
from dmc30000 import DMC30000
driver = DMC30000()
driver.connect(str(ip_addr)) # ip_addr must be ip address of the galil and be a string
```
#### Initialize and Set Analog Outputs
```python
driver.initialize()  # required before AO1 can be used as a general analog output
driver.set_analog_output(1, 0.5)  # AO1 to 0.5 V
driver.set_analog_output(2, -1.0)  # AO2 to -1.0 V
driver.get_analog_output(1)  # voltage currently output on AO1
```
#### Disconnect When Done
```python
driver.disconnect()
```
#### Useful Other Command
```python
driver._send_command("MG@AO[1]") # or 2
driver._read_reply()
```

## Useful Windows commmands
`.\.venv\Scripts\activate.ps1` to activate venv
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` to temporarily allow scripts to run
`Set-ExecutionPolicy RemoteSigned` to perminantly allow scripts to run (requires administrative privileges)
`ipconfig` to find current ip and subnet
