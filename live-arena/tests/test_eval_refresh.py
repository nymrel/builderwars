"""Provenance regressions in upstream imports, without network or eval execution."""
import importlib.util
import unittest,json,tempfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('eval_refresh',Path(__file__).parents[1]/'scripts/refresh-eval-rankings.py')
refresh=importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)

class ProvenanceTests(unittest.TestCase):
 def test_false_strings_are_not_organizer_verification(self):
  for value in (False,None,'false (See README.md for info)','true',1):
   self.assertNotIn('Organizer-checked',refresh.swe_detail({'checked':value}))
  self.assertIn('Organizer-checked',refresh.swe_detail({'checked':True}))

 def test_harness_configuration_survives_extraction(self):
  detail=refresh.swe_detail({'agent':'mini-SWE-agent','mini-swe-agent_version':'1.16.0','reasoning_effort':'medium','tags':['System: Attempts - 1']})
  for expected in ('1.16.0','medium','Attempts - 1'):self.assertIn(expected,detail)

 def test_original_capture_time_is_preserved_and_future_rejected(self):
  original='2025-01-02T03:04:05Z'
  self.assertEqual(refresh.capture_time(original),original)
  for invalid in ('tomorrow','2026-02-30T00:00:00Z','2999-01-01T00:00:00Z'):
   with self.assertRaises(ValueError):refresh.capture_time(invalid)

 def test_offline_metadata_fails_closed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for value in ({},None,False,[],{'capturedAt':'2025-01-02T03:04:05Z','sources':{}}):
    (root/'capture-metadata.json').write_text(json.dumps(value))
    with self.assertRaises(ValueError):refresh.read_capture_metadata(root)
   value={'capturedAt':'2025-01-02T03:04:05Z','sources':{k:{'url':u,'file':f,'sha256':'a'*64} for k,(u,f) in refresh.SOURCES.items()}}
   (root/'capture-metadata.json').write_text(json.dumps(value))
   self.assertEqual(refresh.read_capture_metadata(root)['capturedAt'],value['capturedAt'])
   value['sources']['swe']['sha256']='invalid'
   (root/'capture-metadata.json').write_text(json.dumps(value))
   with self.assertRaises(ValueError):refresh.read_capture_metadata(root)

if __name__=='__main__':unittest.main()
