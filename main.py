import asyncio
import sys
import time

import paho.mqtt.client as paho

broker = "192.168.1.11"
port = 1883

localIP = "0.0.0.0"
localPort = 1200

phaseCnt = 1
lastPhaseSwitch = time.time() - 300

gPower = 0.0
gAllow = 0


def fatal_error(message, error=None):
	if error is not None:
		print(f"ERROR: {message}: {error}")
	else:
		print(f"ERROR: {message}")
	sys.exit(1)


def handle_message(message):
	global gPower, gAllow
	if message.startswith('Power='):
		power = float(message.split('=', 1)[1])
		gPower = min(power, 11)
		print(f'publish power={gPower}')
		publish()
	elif message.startswith('Allow='):
		allow = int(message.split('=', 1)[1])
		gAllow = allow
		print(f'publish allow={gAllow}')
		publish()


class UDP2MQTT(asyncio.DatagramProtocol):
	def connection_made(self, transport):
		self.transport = transport

	def datagram_received(self, data, addr):
		try:
			message = data.decode()
			print(f"Received {message} from {addr}")
			handle_message(message)
		except SystemExit:
			raise
		except Exception as error:
			fatal_error("failed to process UDP packet", error)


async def run_server():
	print("Starting UDP server")
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
	phaseCntNew = 1 if gPower < 4.0 else 3
	print(f'gPower={gPower}, phaseCntNew={phaseCntNew}')
	if phaseCnt is not None and phaseCnt != phaseCntNew:
		now = time.time()
		diff = int(now - lastPhaseSwitch)
		print(f'diff={diff}')
		if diff > 300:
			phaseCnt = phaseCntNew
			lastPhaseSwitch = now
	psm = '1' if phaseCnt < 2 else '2'
	current = int(round(gPower * 1000.0 / (230.0 * phaseCnt)))
	current = max(6, min(16, current))
	frc = 2 if gAllow == 1 else 1
	print(f'publish phaseCnt={phaseCnt}, current={current}, frc={frc} gAllow={gAllow}')
	client = paho.Client(paho.CallbackAPIVersion.VERSION1)
	try:
		client.connect(broker, port)
		publish_result = client.publish("go-eCharger/052332/amp/set", current)
		if publish_result.rc != paho.MQTT_ERR_SUCCESS:
			fatal_error(f"failed to publish current, return code {publish_result.rc}")
		publish_result = client.publish("go-eCharger/052332/psm/set", psm)
		if publish_result.rc != paho.MQTT_ERR_SUCCESS:
			fatal_error(f"failed to publish phase switch mode, return code {publish_result.rc}")
		publish_result = client.publish("go-eCharger/052332/frc/set", frc)
		if publish_result.rc != paho.MQTT_ERR_SUCCESS:
			fatal_error(f"failed to publish force state, return code {publish_result.rc}")
	except SystemExit:
		raise
	except Exception as error:
		fatal_error("failed to publish MQTT messages", error)
	finally:
		client.disconnect()


if __name__ == '__main__':
	try:
		asyncio.run(run_server())
	except SystemExit:
		raise
	except Exception as error:
		fatal_error("server stopped unexpectedly", error)
