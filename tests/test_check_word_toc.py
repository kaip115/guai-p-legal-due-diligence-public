from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_word_toc import check

class WordTocTests(unittest.TestCase):
    def run_case(self, page_number, footer='7', field=True):
        with TemporaryDirectory() as temp:
            report = Path(temp) / 'report.docx'
            body = f"""
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
              <w:p><w:r><w:instrText>{' TOC ' if field else ''}</w:instrText></w:r>
                <w:hyperlink w:anchor="_Toc1"><w:r><w:t>定义</w:t></w:r>
                  <w:r><w:instrText> PAGEREF _Toc1 </w:instrText></w:r>
                  <w:r><w:t>{page_number}</w:t></w:r></w:hyperlink></w:p>
              <w:p><w:bookmarkStart w:name="_Toc1"/><w:r><w:t>定义</w:t></w:r></w:p>
            </w:body></w:document>"""
            with ZipFile(report, 'w') as z:
                z.writestr('word/document.xml', body)
            return check(report, f'目录\n定义........{page_number}\n6\f定义\n第 1 行\n{footer}\f')

    def test_matches_actual_printed_footer_not_physical_page(self):
        self.assertEqual(self.run_case('7'), (1, []))

    def test_rejects_stale_page_number(self):
        self.assertIn('实际页脚为 7', self.run_case('8')[1][0])

    def test_requires_manual_check_for_roman_footer(self):
        self.assertIn('需在 Word 中核对', self.run_case('7', 'vii')[1][0])

    def test_rejects_static_directory(self):
        self.assertIn('未发现', self.run_case('7', field=False)[1][0])

if __name__ == '__main__':
    unittest.main()
