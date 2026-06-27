import sys
import types
import unittest
from unittest.mock import patch

paho_module = types.ModuleType('paho')
mqtt_module = types.ModuleType('paho.mqtt')
client_module = types.ModuleType('paho.mqtt.client')
client_module.CallbackAPIVersion = types.SimpleNamespace(VERSION1=1)
client_module.MQTT_ERR_SUCCESS = 0
client_module.Client = object
paho_module.mqtt = mqtt_module
mqtt_module.client = client_module
sys.modules.setdefault('paho', paho_module)
sys.modules.setdefault('paho.mqtt', mqtt_module)
sys.modules.setdefault('paho.mqtt.client', client_module)

import main


class HandleMessageTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
