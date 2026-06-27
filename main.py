import asyncio
import socket
import paho.mqtt.client as paho
import re
import time
broker="192.168.1.11"
port=1883


localIP     = "0.0.0.0"
localPort   = 1200
bufferSize  = 1024

phaseCnt = 1
lastPhaseSwitch = time.time() - 300

gPower = 0.
gAllow = 0

class UDP2MQTT(asyncio.DatagramProtocol):
	def connection_made(self, transport):
		self.transport = transport

	def datagram_received(self, data, addr):
		global gPower, gAllow
		message = data.decode()
		print(f"Received {message} from {addr}")
		m = re.match(r'Power=([\d\.\d]+)', message)
		if m:
			gPower = min(float(m.group(1)), 11)
			print(f'publish power={gPower}')
			publish()
		m = re.match(r'Allow=(\d)', message)
		if m:
			gAllow = int(m.group(1))
			print(f'publish allow={gAllow}')
			publish()


async def run_server():
	global gPower, gAllow
	print("Starting UDP server")
	# Bind to localhost on UDP port 8888
	loop = asyncio.get_running_loop()
	transport, _ = await loop.create_datagram_endpoint(
		lambda: UDP2MQTT(),
		local_addr=(localIP, localPort)
	)

	try:
		while True:
			await asyncio.sleep(60)
	finally:
		transport.close()


def publish():
	global gPower, phaseCnt, lastPhaseSwitch, gAllow
	phaseCntNew  = 1 if gPower < 4. else 3
	print(f'gPower={gPower}, phaseCntNew={phaseCntNew}')
	if phaseCnt is not None and phaseCnt != phaseCntNew:
		now = time.time()
		diff = int(now - lastPhaseSwitch)
		print(f'diff={diff}')
		if diff > 300:
			phaseCnt = phaseCntNew
			lastPhaseSwitch = now
	psm = '1' if phaseCnt < 2 else '2'
	current = int(round(gPower * 1000. / (230. * phaseCnt)))
	current = max(6, min(16, current))
	frc = 2 if gAllow == 1 else 1
	print(f'publish phaseCnt={phaseCnt}, current={current}, frc={frc} gAllow={gAllow}') 
	client = paho.Client(paho.CallbackAPIVersion.VERSION1)   
	def on_connect(client, userdata, flags, rc):
		if rc == 0:
			print("Connected to MQTT Broker!")
		else:
			print("Failed to connect, return code %d\n", rc)
	client.connect(broker, port)
	client.publish("go-eCharger/052332/amp/set", current) 
	client.publish("go-eCharger/052332/psm/set", psm)
	client.publish("go-eCharger/052332/frc/set", frc) 


if __name__ == '__main__':
	asyncio.run(run_server())
