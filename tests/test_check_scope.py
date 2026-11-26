"""Run with python tests/test_check_scope.py. No external packages required."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_scope.py"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class ReportChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "scope.csv").write_text("原范围条项\nA\n", encoding="utf8")
        (self.root / "map.csv").write_text("原范围条项,报告位置\nA,经营\n", encoding="utf8")

    def check(self, report, code, *options):
        result = subprocess.run([sys.executable, str(SCRIPT), "--scope", "scope.csv",
                                 "--mapping", "map.csv", "--report", report, *options],
                                cwd=self.root, encoding="utf-8", capture_output=True,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout

    def test_markdown(self):
        report = self.root / "report.md"
        body = ("# 经营\n## 场所\n材料名称 | 日期\n--- | ---\n租约 | 【日期】\n"
                "## 许可\n公司回复\n覆盖报告期。\n\n【本所核对｜第1项】核对许可。")
        report.write_text(body, encoding="utf8")
        out = self.check(report.name, 0)
        self.assertIn("经营｜正文 2 段｜表格 1 张｜本节占位 0 处｜含下级共 1 处", out)
        self.assertIn("场所｜第 5 行（表格）｜【日期】", out)
        self.check(report.name, 1, "--final")
        report.write_text(body.replace("【日期】", "已核") + "\n## 待写\n|名称|\n|---|\n| |", encoding="utf8")
        self.assertIn("待写｜正文 0 段｜表格 0 张｜本节占位 0 处｜含下级共 0 处｜空标题", self.check(report.name, 1))
        report.write_text(body.replace("【日期】", "已核"), encoding="utf8")
        self.check(report.name, 0, "--final")
        (self.root / "map.csv").write_text("原范围条项,报告位置\nX,已改名\n", encoding="utf8")
        out = self.check(report.name, 1)
        for message in ("范围外编号：X", "标题匹配 0 处", "未对应报告位置：A"):
            self.assertIn(message, out)

    def test_heading_paths(self):
        outline = [(1, "报告"), (2, "第一部分 资产"), (3, "一、基本情况"),
                   (2, "第二部分 股权"), (3, "一、基本情况")]
        md = self.root / "report.md"
        md.write_text("".join("#" * level + " " + title + "\n内容。\n"
                              for level, title in outline), encoding="utf8")
        with ZipFile(self.root / "report.docx", "w") as doc:
            blocks = []
            for level, title in outline:
                blocks.append(f'<w:p><w:pPr><w:outlineLvl w:val="{level-1}"/></w:pPr>'
                              f'<w:r><w:t>{title}</w:t></w:r></w:p>'
                              '<w:p><w:r><w:t>内容。</w:t></w:r></w:p>')
            doc.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>'
                         + "".join(blocks) + '</w:body></w:document>')
            doc.writestr("word/styles.xml", f'<w:styles xmlns:w="{W}"/>')
        for report in ("report.md", "report.docx"):
            for title, count in [("一、基本情况", 2), ("第二部分 股权 > 一、基本情况", 1),
                                 ("报告 > 第一部分 资产 > 一、基本情况", 1),
                                 ("其他部分 > 一、基本情况", 0)]:
                with self.subTest(report=report, title=title):
                    (self.root / "map.csv").write_text(f"原范围条项,报告位置\nA,{title}\n", encoding="utf8")
                    output = self.check(report, int(count != 1))
                    if count != 1:
                        self.assertIn(f"标题匹配 {count} 处", output)
                    if count == 2:
                        self.assertIn("候选位置：报告 > 第一部分 资产 > 一、基本情况", output)

    def test_output_encoding(self):
        (self.root / "report.md").write_text("# 经营\n公司已登记。", encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--scope", "scope.csv", "--mapping", "map.csv",
                   "--report", "report.md"]
        env = dict(os.environ, LC_ALL="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        env.pop("PYTHONIOENCODING", None)
        for setting, encoding in [(None, "utf-8"), ("gbk", "gbk")]:
            with self.subTest(encoding=encoding):
                if setting:
                    env["PYTHONIOENCODING"] = setting
                result = subprocess.run(command, cwd=self.root, env=env, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn("范围定位", result.stdout.decode(encoding))
                error = subprocess.run(command[:-1] + ["missing.md"], cwd=self.root, env=env, capture_output=True)
                self.assertNotEqual(error.returncode, 0)
                self.assertIn("输入错误", error.stderr.decode(encoding))

    def test_multiline(self):
        report = self.root / "report.md"
        report.write_text("# 经营\n已收材料。\n截至【基准日为\n下月末】，据【书面回复】。", encoding="utf8")
        output = self.check(report.name, 1, "--final")
        self.assertIn("经营｜第 3 至 4 行｜【基准日为下月末】", output)
        self.assertIn("经营｜第 4 行｜【书面回复】", output)
        self.assertIn("本节占位 2 处｜含下级共 2 处", output)
        self.check(report.name, 0)
        report.write_text("# 经营\n【甲\n\n乙】\n【丙\n## 下一节\n丁】", encoding="utf8")
        self.assertIn("占位位置：共 0 处", self.check(report.name, 0, "--final"))

    def test_english_markers(self):
        report = self.root / "report.md"
        clean = "# 经营\nSee [1], [Closing Date], [TBD](doc.md), and [source][TBC].\n\n[TBC]: doc.md\n"
        report.write_text(clean, encoding="utf8")
        self.check(report.name, 0, "--final")
        report.write_text(clean + "\nAs of [insert the\nclosing date]: [TBD], [XX], [date 1].", encoding="utf8")
        out = self.check(report.name, 1, "--final")
        self.assertIn("第 6 至 7 行｜[insert the closing date]", out)
        self.assertIn("占位位置：共 4 处", out)

    def check_note(self, tag, label, note_id):
        for token, status in [("【出处】", 1), ("[TBC]", 1), ("文献甲，第十页。", 0)]:
            with ZipFile(self.root / "report.docx", "w") as doc:
                doc.writestr("word/styles.xml", f'<w:styles xmlns:w="{W}"/>')
                doc.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>'
                             '<w:p><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:r><w:t>经营</w:t></w:r></w:p>'
                             f'<w:p><w:r><w:t>已核实。</w:t><w:{tag}Reference w:id="{note_id}"/></w:r></w:p>'
                             '</w:body></w:document>')
                doc.writestr(f"word/{tag}s.xml", f'<w:{tag}s xmlns:w="{W}"><w:{tag} w:id="{note_id}">'
                             '<w:p><w:r><w:t>引用资料</w:t></w:r></w:p>'
                             f'<w:p><w:r><w:t>{token[:2]}</w:t></w:r><w:r><w:t>{token[2:]}</w:t></w:r></w:p>'
                             f'</w:{tag}></w:{tag}s>')
            output = self.check("report.docx", 0)
            self.assertIn(f"占位位置：共 {status} 处", output)
            self.assertIn("Word 批注：共 0 条", output)
            if status:
                self.assertIn(f"{label} ID {note_id} 第 2 段｜{token}", output)
            self.check("report.docx", status, "--final")

    def test_word_footnote(self):
        self.check_note("footnote", "脚注", 3)

    def test_word_endnote(self):
        self.check_note("endnote", "尾注", 2)

    def test_word(self):
        heading = '<w:p><w:pPr><w:pStyle w:val="H"/></w:pPr><w:r><w:t>经营</w:t></w:r></w:p>'
        def row(text, header=False):
            flag = "<w:trPr><w:tblHeader/></w:trPr>" if header else ""
            return f"<w:tr>{flag}<w:tc><w:p>{text}</w:p></w:tc></w:tr>"
        top = row("<w:r><w:t>名称</w:t></w:r>", True)
        def write(data):
            with ZipFile(self.root / "report.docx", "w") as doc:
                doc.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body>{heading}'
                             f'<w:tbl>{top}{row(data)}</w:tbl></w:body></w:document>')
                doc.writestr("word/styles.xml", f'<w:styles xmlns:w="{W}"><w:style w:styleId="H">'
                             '<w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style></w:styles>')
        write("<w:r><w:t>【基</w:t></w:r><w:r><w:t>准日】</w:t></w:r>")
        out = self.check("report.docx", 0)
        self.assertIn("经营｜表 1 第 2 行第 1 格｜【基准日】", out)
        self.check("report.docx", 1, "--final")
        write("<w:r><w:t>已核实</w:t></w:r>")
        with ZipFile(self.root / "report.docx", "a") as doc:
            doc.writestr("word/comments.xml", f'<w:comments xmlns:w="{W}"><w:comment w:id="7">'
                         '<w:p><w:r><w:t>【请公司确认｜第1项】请确认。</w:t></w:r></w:p>'
                         '</w:comment></w:comments>')
        output = self.check("report.docx", 1, "--final")
        self.assertIn("Word 批注：共 1 条", output)
        self.assertIn("占位位置：共 0 处", output)
        self.check("report.docx", 0)
        write("<w:r><w:t>已核实</w:t></w:r>")
        with ZipFile(self.root / "report.docx", "a") as doc:
            for part, tag in [("header2", "hdr"), ("footer1", "ftr")]:
                doc.writestr(f"word/{part}.xml", f'<w:{tag} xmlns:w="{W}"><w:p><w:r><w:t>【日</w:t></w:r>'
                             f'<w:r><w:t>期】</w:t></w:r></w:p></w:{tag}>')
        output = self.check("report.docx", 1, "--final")
        self.assertIn("页眉 header2 第 1 段｜【日期】", output)
        self.assertIn("页脚 footer1 第 1 段｜【日期】", output)
        self.assertIn("占位位置：共 2 处", output)
        with ZipFile(self.root / "report.docx", "a") as doc:
            doc.writestr("word/comments.xml", f'<w:comments xmlns:w="{W}"><w:comment w:id="9">'
                         '<w:p><w:r><w:t>收到【章程证明日】资料。</w:t></w:r></w:p>'
                         '</w:comment></w:comments>')
        output = self.check("report.docx", 0)
        self.assertIn("批注 ID 9 第 1 段｜【章程证明日】", output)
        self.assertIn("占位位置：共 3 处", output)
        write("<w:r><w:t>已核实</w:t></w:r>")
        self.check("report.docx", 0, "--final")
        write("")
        self.assertIn("空标题", self.check("report.docx", 1))


if __name__ == "__main__":
    unittest.main()
