import subprocess, sys, unittest
from pathlib import Path

class SampleRegression(unittest.TestCase):
    def test_word_and_markdown(self):
        root=Path(__file__).resolve().parents[1]
        for report in ('references/sample-focused-report.md','assets/sample-focused-report.docx'):
            with self.subTest(report=report):
                result=subprocess.run([sys.executable,'scripts/check_scope.py','--scope','references/sample-scope.md','--section','核查事项','--mapping','references/sample-report-map.csv','--report',report,'--final'],cwd=root,capture_output=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
                self.assertIn('所列标题均可唯一定位 7 项',result.stdout)
