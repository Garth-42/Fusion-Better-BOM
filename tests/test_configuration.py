import unittest
from FusionConfigurableBOM.persistence.configuration_store import default_configuration, dumps, loads, ConfigurationError, _ensure_default_views, FusionConfigurationStore

class _StubAttribute:
 def __init__(self,value): self.value=value
class _StubAttributes:
 def __init__(self,value): self._attribute=_StubAttribute(value)
 def itemByName(self,group,name): return self._attribute
class _StubRoot:
 def __init__(self,value): self.attributes=_StubAttributes(value)

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
 def test_ensure_default_views_restores_a_missing_structured_view(self):
  # A design configured before the Structured BOM shipped keeps only its flat views.
  config=loads('{"schema_version":2,"fields":[],"views":[{"view_id":"general","name":"General BOM","structure":"flat","columns":[]}]}')
  _ensure_default_views(config)
  structures={v.view_id:v.structure for v in config.views}
  self.assertEqual(structures.get('structured'),'hierarchical'); self.assertIn('purchasing_demo',structures)
  self.assertEqual(1,sum(1 for v in config.views if v.view_id=='general'))
 def test_ensure_default_views_leaves_existing_views_untouched(self):
  config=default_configuration(); config.views[0].name='My General'
  _ensure_default_views(config)
  self.assertEqual('My General',next(v.name for v in config.views if v.view_id=='general'))
  self.assertEqual(3,len(config.views))
 def test_store_load_adds_the_structured_view_to_a_legacy_design(self):
  # End to end through the store: a legacy v1 design (no Structured BOM) migrates
  # to v2 and gains the hierarchical format so it appears in the format picker.
  legacy='{"schema_version":1,"fields":[],"views":[{"view_id":"general","name":"General BOM","columns":[]},{"view_id":"purchasing_demo","name":"Purchasing Demo","columns":[]}]}'
  config=FusionConfigurationStore().load(_StubRoot(legacy))
  self.assertEqual(config.schema_version,2)
  self.assertEqual('hierarchical',next(v.structure for v in config.views if v.view_id=='structured'))
