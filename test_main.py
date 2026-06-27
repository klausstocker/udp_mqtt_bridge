import sys
import types
import unittest
from unittest.mock import patch

paho_module = types.ModuleType('paho')
mqtt_module = types.ModuleType('paho.mqtt')
client_module = types.ModuleType('paho.mqtt.client')
client_module.CallbackAPIVersion = types.SimpleNamespace(VERSION1=1)
client_module.MQTT_ERR_SUCCESS = 0


class PublishResult:
    rc = 0


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def connect(self, broker, port):
        self.broker = broker
        self.port = port

    def publish(self, topic, value):
        return PublishResult()

    def disconnect(self):
        self.disconnected = True


client_module.Client = FakeClient
paho_module.mqtt = mqtt_module
mqtt_module.client = client_module
sys.modules.setdefault('paho', paho_module)
sys.modules.setdefault('paho.mqtt', mqtt_module)
sys.modules.setdefault('paho.mqtt.client', client_module)

import main


class FakeHandle:
    def __init__(self):
        self.cancelled_called = False

    def cancel(self):
        self.cancelled_called = True

    def cancelled(self):
        return self.cancelled_called


class FakeLoop:
    def __init__(self):
        self.delay = None
        self.callback = None
        self.handle = FakeHandle()

    def call_later(self, delay, callback):
        self.delay = delay
        self.callback = callback
        return self.handle


class HandleMessageTest(unittest.TestCase):
    def tearDown(self):
        if main.phaseSwitchRetry is not None:
            main.phaseSwitchRetry.cancel()
            main.phaseSwitchRetry = None

    def test_allow_message_updates_allow_without_power_parse(self):
        main.gAllow = 0
        with patch('main.publish') as publish:
            main.handle_message('Allow=1')
        self.assertEqual(main.gAllow, 1)
        publish.assert_called_once_with()

    def test_power_message_updates_power(self):
        main.gPower = 0.0
        with patch('main.publish') as publish:
            main.handle_message('Power=7.5')
        self.assertEqual(main.gPower, 7.5)
        publish.assert_called_once_with()

    def test_publish_schedules_retry_when_phase_switch_must_wait(self):
        fake_loop = FakeLoop()
        main.gPower = 5.0
        main.gAllow = 1
        main.phaseCnt = 1
        main.lastPhaseSwitch = 100.0
        main.phaseSwitchRetry = None

        with patch('main.time.time', return_value=200.0), \
                patch('main.asyncio.get_running_loop', return_value=fake_loop):
            main.publish()

        self.assertIs(main.phaseSwitchRetry, fake_loop.handle)
        self.assertEqual(fake_loop.callback, main.publish)
        self.assertAlmostEqual(fake_loop.delay, 200.1)
        self.assertEqual(main.phaseCnt, 1)


if __name__ == '__main__':
    unittest.main()
