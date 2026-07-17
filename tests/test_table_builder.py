import unittest
from FusionConfigurableBOM.domain.models import ConceptBomRow, HierarchicalBomNode, BomTableFormat, ColumnDefinition
from FusionConfigurableBOM.domain.table_builder import build_table
class TableTests(unittest.TestCase):
 def test_visible_columns_and_attribute_values(self):
  row=ConceptBomRow('a','Same name',3,custom_values={'manufacturer':'Acme'})
  view=BomTableFormat('v','V',[ColumnDefinition('builtin','quantity','Qty'),ColumnDefinition('attribute','manufacturer','Maker'),ColumnDefinition('builtin','component_name','Hidden',False)])
  table=build_table([row],view); self.assertEqual([c['header'] for c in table['columns']],['Qty','Maker']); self.assertEqual(table['rows'][0]['values']['manufacturer'],'Acme')
 def test_same_name_rows_remain_distinct(self):
  view=BomTableFormat('v','V',[ColumnDefinition('builtin','component_name','Component')])
  rows=[ConceptBomRow('a','Bracket',1),ConceptBomRow('b','Bracket',2)]
  self.assertEqual(len(build_table(rows,view)['rows']),2)
 def test_flat_view_reports_structure_and_omits_tree_metadata(self):
  view=BomTableFormat('v','V',[ColumnDefinition('builtin','component_name','Component')])
  table=build_table([ConceptBomRow('a','Bracket',1)],view)
  self.assertEqual(table['structure'],'flat'); self.assertNotIn('level',table['rows'][0])
  self.assertEqual(table['rollup_by'],'component')
 def test_hierarchical_view_emits_tree_metadata_and_total_quantity(self):
  view=BomTableFormat('v','V',[ColumnDefinition('builtin','component_name','Component'),ColumnDefinition('builtin','total_quantity','Total')],'hierarchical')
  parent=HierarchicalBomNode('r1','Gearbox',0,None,2,2,True)
  child=HierarchicalBomNode('r2','Screw',1,'r1',4,8,False)
  table=build_table([parent,child],view)
  self.assertEqual(table['structure'],'hierarchical')
  self.assertEqual([r['level'] for r in table['rows']],[0,1])
  self.assertTrue(table['rows'][0]['is_assembly']); self.assertFalse(table['rows'][1]['is_assembly'])
  self.assertEqual(table['rows'][1]['parent_id'],'r1'); self.assertEqual(table['rows'][1]['values']['total_quantity'],8)

class _Attributes:
 def itemByName(self, group, name): return None
class _MapAttribute:
 def __init__(self,value): self.value=value
class _MapAttributes:
 def __init__(self): self._store={}
 def itemByName(self,group,name): return self._store.get((group,name))
 def add(self,group,name,value):
  attribute=_MapAttribute(value); self._store[(group,name)]=attribute; return attribute
class _Component:
 def __init__(self,name,entity_token=None): self.name=name; self.entityToken=entity_token; self.attributes=_Attributes(); self.partNumber=''; self.description=''; self.material=None; self.isReferencedComponent=False
class _Children:
 count=0
class _NonLeafChildren:
 count=1
class _Occurrence:
 def __init__(self,component,children=None): self.component=component; self.childOccurrences=children or _Children(); self.isSuppressed=False
class _Root:
 def __init__(self,occurrences,root_occurrences=None): self.allOccurrences=occurrences; self.occurrences=root_occurrences or []
class _Design:
 def __init__(self,occurrences): self.rootComponent=_Root(occurrences)
class ScannerTests(unittest.TestCase):
 def test_repeated_component_definitions_are_aggregated(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  repeated=_Component('Bracket'); distinct=_Component('Bracket')
  rows,_=scan_design(_Design([_Occurrence(repeated),_Occurrence(repeated),_Occurrence(repeated),_Occurrence(distinct)]),[])
  self.assertEqual(sorted(row.quantity for row in rows),[1,3])
 def test_component_proxies_with_the_same_entity_token_are_aggregated(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  first_proxy=_Component('Bracket','component-token-1'); second_proxy=_Component('Bracket','component-token-1')
  rows,_=scan_design(_Design([_Occurrence(first_proxy),_Occurrence(second_proxy)]),[])
  self.assertEqual([(row.component_name, row.quantity) for row in rows],[('Bracket',2)])
 def test_non_leaf_only_assembly_falls_back_to_visible_occurrences(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  component=_Component('Imported assembly')
  rows,_=scan_design(_Design([_Occurrence(component, _NonLeafChildren())]),[])
  self.assertEqual([(row.component_name, row.quantity) for row in rows],[('Imported assembly',1)])
 def test_empty_all_occurrences_falls_back_to_root_occurrences(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  component=_Component('Direct occurrence')
  design=_Design([]); design.rootComponent.occurrences=[_Occurrence(component)]
  rows,_=scan_design(design,[])
  self.assertEqual([(row.component_name, row.quantity) for row in rows],[('Direct occurrence',1)])
 def test_scan_reads_values_stored_on_the_design_root(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  from FusionConfigurableBOM.fusion import value_store
  component=_Component('Bracket','token-x')
  design=_Design([_Occurrence(component)]); design.rootComponent.attributes=_MapAttributes()
  value_store.write_value(design.rootComponent, component, 'manufacturer', 'Acme')
  rows,_=scan_design(design,['manufacturer'])
  self.assertEqual(rows[0].custom_values['manufacturer'],'Acme')
