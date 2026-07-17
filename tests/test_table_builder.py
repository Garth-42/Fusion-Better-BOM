import unittest
from FusionConfigurableBOM.domain.models import ConceptBomRow, BomTableFormat, ColumnDefinition
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

class _Attributes:
 def itemByName(self, group, name): return None
class _Component:
 def __init__(self,name): self.name=name; self.attributes=_Attributes(); self.partNumber=''; self.description=''; self.material=None; self.isReferencedComponent=False
class _Children:
 count=0
class _Occurrence:
 def __init__(self,component): self.component=component; self.childOccurrences=_Children(); self.isSuppressed=False
class _Root:
 def __init__(self,occurrences): self.allOccurrences=occurrences
class _Design:
 def __init__(self,occurrences): self.rootComponent=_Root(occurrences)
class ScannerTests(unittest.TestCase):
 def test_repeated_component_definitions_are_aggregated(self):
  from FusionConfigurableBOM.fusion.assembly_scanner import scan_design
  repeated=_Component('Bracket'); distinct=_Component('Bracket')
  rows,_=scan_design(_Design([_Occurrence(repeated),_Occurrence(repeated),_Occurrence(repeated),_Occurrence(distinct)]),[])
  self.assertEqual(sorted(row.quantity for row in rows),[1,3])
