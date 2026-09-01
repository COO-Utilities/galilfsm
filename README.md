This is a Galil Driver for the galil that will connect to the FSM

for this to work you need to have gclib installed on your machine
you can do this on Windows or Linux but on macos you have to do some shenanigins (rosetta 2)

## Installing Galil gclib on Linux

```bash
uv sync
source .venv/bin/activate
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
gclib.assign_ip(f'{mac_address}', f'{ip_addr}')
```
#### Connect Controller
```python
import galil_driver
driver = galil_driver.GalilDeviceController()
driver.connect(str(ip_addr)) # ip_addr must be ip address of the galil and be a string
```
#### Initialize and Set Position
```python
driver.initialize()
x_volts, y_volts = 0, 0
driver.send_position_voltage(x_pos,y_pos)
# alternative commands
# driver.x_voltage=x_volts
# driver.y_voltage=y_volts
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
