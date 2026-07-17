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
 def test_v1_configuration_migrates_to_flat_views(self):
  config=loads('{"schema_version":1,"fields":[],"views":[{"view_id":"v","name":"V","columns":[]}]}')
  self.assertEqual(config.schema_version,2); self.assertEqual(config.views[0].structure,'flat')
 def test_default_configuration_includes_a_hierarchical_view(self):
  structures={v.view_id:v.structure for v in default_configuration().views}
  self.assertEqual(structures['general'],'flat'); self.assertEqual(structures['structured'],'hierarchical')
 def test_structure_round_trips(self):
  self.assertEqual(loads(dumps(default_configuration())).views[2].structure,'hierarchical')
 def test_invalid_structure_is_rejected(self):
  with self.assertRaises(ConfigurationError): loads('{"schema_version":2,"fields":[],"views":[{"view_id":"v","name":"V","structure":"bogus","columns":[]}]}')
