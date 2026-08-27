This is a Galil Driver for the galil that will connect to the FSM

for this to work you need to have gclib installed on your machine
you can do this on Windows or Linux but on macos you have to do some shenanigins (rosetta 2)

## Installing Galil gclib on Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade --index-url https://www.galil.com/sw/pub/python gclib
```

check version

```python
import gclib
gclib.version()
```

`'2.5.0'`

## How to assign IP address to Galil

```python
import gclib
print(gclib.ip_requests())
# find address you want
# define variables mac_address and ip_addr or just input directly
gclib.assign_ip(f'{mac_address}', f'{ip_addr}')
```
