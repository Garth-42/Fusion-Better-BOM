import unittest
from FusionConfigurableBOM.persistence.configuration_store import default_configuration, dumps, loads, ConfigurationError
class ConfigurationTests(unittest.TestCase):
 def test_round_trip(self):
  config=default_configuration(); self.assertEqual(loads(dumps(config)).views[1].columns[2].source_id,'manufacturer')
 def test_headers_are_view_specific(self):
  config=default_configuration(); config.views[1].columns[2]=config.views[1].columns[2].__class__('attribute','manufacturer','Maker')
  self.assertEqual(loads(dumps(config)).views[1].columns[2].header,'Maker')
 def test_unknown_schema_is_rejected(self):
  with self.assertRaises(ConfigurationError): loads('{"schema_version":99,"fields":[],"views":[]}')
 def test_invalid_field_id_is_rejected(self):
  with self.assertRaises(ConfigurationError): loads('{"schema_version":1,"fields":[{"field_id":"Bad Name","default_label":"Bad"}],"views":[{"view_id":"v","name":"V","columns":[]}]}')
