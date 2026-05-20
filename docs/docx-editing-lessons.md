# Lessons Learned: Programmatic .docx Editing

A reference guide for AI agents (or humans) modifying Microsoft Word .docx files via XML manipulation. Captured from a real session that edited symbols, units, and inserted nomenclature tables into a scientific manuscript.

---

## 1. Understand the .docx Format First

A `.docx` is a **ZIP archive** containing XML files. The main content lives in `word/document.xml`.

```
mydoc.docx (zip)
├── [Content_Types].xml
├── _rels/
├── word/
│   ├── document.xml         ← Main content (edit this)
│   ├── styles.xml
│   ├── numbering.xml
│   ├── comments.xml
│   ├── footer1.xml, header1.xml
│   ├── settings.xml
│   └── media/               ← Images
├── docProps/
└── customXml/
```

**Workflow**:
1. Unzip to a temp directory
2. Edit `word/document.xml` (and possibly other XML files)
3. Re-zip the directory contents (NOT the directory itself) into a new `.docx`

```bash
# Extract
unzip -q mydoc.docx -d /tmp/docx_extract

# Edit /tmp/docx_extract/word/document.xml ...

# Repackage (must zip from inside the directory!)
cd /tmp/docx_extract && zip -r -q /tmp/newdoc.docx . -x ".DS_Store"
```

---

## 2. Never Trust .docx → .txt Conversions for Math

Math equations, Greek letters, and subscripts in Word are stored as **OOXML Math (OMML)**, not as plain Unicode text inside `<w:t>` elements.

When you convert to .txt (via `textutil`, `pandoc`, or copy-paste), **OMML content gets stripped or mangled silently**:

```
Original Word doc:  K_d = C_0 · α_ice² / [(1-α_ice)³ + ε_0]
.txt conversion:    K_d =  ·  ² / [(1- )³ +  ]     ← symbols GONE
```

**Always read math directly from `word/document.xml`** by parsing `<m:t>...</m:t>` elements (OMML text).

```python
import re
with open('word/document.xml') as f:
    xml = f.read()
math_symbols = re.findall(r'<m:t>([^<]*)</m:t>', xml)
```

---

## 3. OMML Structure Cheat Sheet

The math markup has a specific structure you need to understand before editing:

### Basic run (one math character)
```xml
<m:r>
  <w:rPr>...font/color properties...</w:rPr>
  <m:t>X</m:t>
</m:r>
```

### Subscripted variable (e.g., K_d)
```xml
<m:sSub>
  <m:e>                         ← BASE
    <m:r><m:t>K</m:t></m:r>
  </m:e>
  <m:sub>                       ← SUBSCRIPT
    <m:r><m:t>d</m:t></m:r>
  </m:sub>
</m:sSub>
```

### Superscript: same pattern with `<m:sSup>`, `<m:sup>`

### Important quirks
- A symbol's text may be **split across multiple `<m:t>` elements** (e.g., "shared" may appear as `<m:t>s</m:t><m:t>h</m:t><m:t>ared</m:t>` if Word's editor did weird things)
- Word adds **rsid attributes everywhere** (`w:rsidR`, `w:rsidRPr`, etc.) — preserve them when editing existing runs
- Always wrap inserted text content with `xml:space="preserve"` when it has leading/trailing spaces

---

## 4. THE GOLDEN RULE: No Greedy Regex Across Tags

**This is the #1 mistake.** Greedy regex patterns like `<m:sSub>.*?</m:sSub>` with `re.DOTALL` can consume MUCH more XML than intended, breaking the entire document structure.

### Dangerous approach
```python
# This often consumes the wrong closing tag
pattern = re.compile(r'<m:sSub>.*?<m:t>θ</m:t>.*?<m:t>c</m:t>.*?</m:sSub>', re.DOTALL)
```

### Safe approach: Position-based with context check
```python
# 1. Find every candidate position
positions = [(m.start(), m.end()) for m in re.finditer(r'<m:t>α</m:t>', xml)]

# 2. For each position, look at the NEXT m:t element to decide
to_replace = []
for s, e in positions:
    following = xml[e:e+800]  # bounded lookahead
    next_match = re.search(r'<m:t>([^<]*)</m:t>', following)
    next_text = next_match.group(1) if next_match else ''
    if next_text == 'c':  # this α is followed by c subscript → α_c
        to_replace.append((s, e))

# 3. Apply from end to start (so earlier positions don't shift)
for s, e in reversed(to_replace):
    xml = xml[:s] + '<m:t>θ</m:t>' + xml[e:]
```

**Key principles**:
- Find isolated **anchor points** (single `<m:t>` elements)
- **Look forward/backward** for disambiguating context
- **Replace from end to start** so positions don't shift mid-loop
- After every batch of edits, **validate the XML** with `ET.parse()`

---

## 5. Always Validate XML After Every Edit Batch

Catch corruption immediately, not at the end:

```python
import xml.etree.ElementTree as ET
try:
    ET.parse('word/document.xml')
    print('XML still valid')
except Exception as e:
    print(f'XML BROKEN: {e}')
    # Restore from backup, debug
```

If you wait until the final repackaging to discover corruption, you lose all context about which edit broke it.

---

## 6. Always Make a Backup BEFORE Touching Anything

Trivial but essential:

```bash
cp "MyDocument.docx" "MyDocument_BACKUP_pre_edits.docx"
```

If anything goes wrong, restore with:
```bash
cp "MyDocument_BACKUP_pre_edits.docx" "MyDocument.docx"
```

Do this **before each significant edit pass**, not just once at the beginning. The backup file should be named with the date or edit context (e.g., `_BACKUP_pre_nomenclature_fix`).

---

## 7. Symbol Disambiguation by Context

The same Unicode character often means different things in different places. Examples from a real frost CFD paper:

| Symbol | Possible meanings | How to disambiguate |
|---|---|---|
| `α` | Ice volume fraction, humid-air volume fraction, contact angle, learnable scaling coefficient | Check the **next `<m:t>`** for the subscript (`ice`, `ha`, `c`, `physics`) |
| `θ` | Contact angle, neural network parameters | Check next text: bare → angle; `shared` → network |
| `ω` | Humidity ratio, loss weight | Check next text: `air`, `air,i` → humidity; `timestep`, `case` → weight |
| `K` | Darcy drag coefficient (variable), temperature unit (Kelvin) | Check if it's in `<m:e>` (subscript base = variable) or standalone (unit) |

**Lesson**: Don't do blind find-and-replace on Greek letters. Always check the surrounding context first.

---

## 8. Choose the Right Replacement Strategy

| Replacement Type | Strategy | Risk |
|---|---|---|
| **Pure text inside `<m:t>`** (e.g., `frost,ini` → `frost,0`) | Direct `str.replace()` | Low |
| **Single symbol change** (e.g., `α` → `θ`) | Context-aware position-based | Medium |
| **Structural change** (e.g., remove a subscript) | Surgical block extraction, then reinsertion | High |
| **Inserting whole tables/sections** | Build OOXML carefully, validate after | High |

The simpler the operation, the more direct your tool can be. Reserve regex with backreferences and structural surgery for cases where simpler approaches won't work.

---

## 9. Building New OOXML from Scratch (e.g., Tables)

When inserting whole new structures like a table, build the minimal valid OOXML:

```xml
<w:tbl>
  <w:tblPr>
    <w:tblStyle w:val="TableGrid"/>
    <w:tblW w:w="9000" w:type="dxa"/>
    <w:tblBorders>...</w:tblBorders>
    <w:tblLook w:val="04A0"/>
  </w:tblPr>
  <w:tblGrid>
    <w:gridCol w:w="3000"/>
    <w:gridCol w:w="6000"/>
  </w:tblGrid>
  <w:tr>
    <w:tc>
      <w:tcPr><w:tcW w:w="3000" w:type="dxa"/></w:tcPr>
      <w:p><w:r><w:t>Cell content</w:t></w:r></w:p>
    </w:tc>
    ...
  </w:tr>
</w:tbl>
```

**Things to remember**:
- Every cell **must** contain at least one `<w:p>` (paragraph), even if empty
- `<w:tblGrid>` column widths should sum to `<w:tblW>` width
- Table widths are in **dxa** (1/20 of a point, ~1/1440 of an inch)
- For best style consistency, **template off an existing table in the document** when possible

---

## 10. Marking Modifications in Red (for Review Highlighting)

To mark a modification visually, add `<w:color w:val="FF0000"/>` to the run properties (`<w:rPr>`).

### For a text run:
```xml
<w:r>
  <w:rPr>
    <w:color w:val="FF0000"/>
    <w:sz w:val="24"/>
  </w:rPr>
  <w:t>Modified text</w:t>
</w:r>
```

### For a math run:
```xml
<m:r>
  <w:rPr>
    <w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>
    <w:color w:val="FF0000"/>
  </w:rPr>
  <m:t>Θ</m:t>
</m:r>
```

### When modifying existing runs, INJECT color into existing `<w:rPr>`:
```python
if '<w:rPr>' in run:
    run = run.replace('<w:rPr>', '<w:rPr><w:color w:val="FF0000"/>', 1)
else:
    # No rPr exists — add one right after the opening run tag
    run = run.replace('<m:r>', '<m:r><w:rPr><w:color w:val="FF0000"/></w:rPr>', 1)
```

This is much friendlier than tracked changes for "tell me what you modified."

---

## 11. Orphaned References Aren't Fatal, But Be Aware

If you delete a paragraph that contained:
- `<w:commentRangeStart w:id="N"/>` and `<w:commentRangeEnd w:id="N"/>`
- `<w:commentReference w:id="N"/>`

The corresponding comment in `word/comments.xml` becomes **orphaned** but is harmless. Word will silently ignore it.

Same applies to:
- Bookmarks (`<w:bookmarkStart/>`, `<w:bookmarkEnd/>`)
- Hyperlinks pointing to deleted text

You can clean these up by editing `comments.xml`, but it's optional.

---

## 12. The Repackaging Gotcha

When zipping back to .docx, you **must zip from inside the extracted directory**, NOT the directory itself:

```bash
# CORRECT
cd /tmp/docx_extract
zip -r -q /tmp/output.docx . -x ".DS_Store"

# WRONG (Word will refuse to open it)
zip -r /tmp/output.docx /tmp/docx_extract/
```

The .docx must have `[Content_Types].xml` at the **root** of the zip archive, not inside a subfolder.

Also exclude `.DS_Store` (on macOS) and any other OS-specific junk files.

---

## 13. Verify Changes by Re-Extracting

After repackaging, **extract again to a new temp directory** and confirm:
1. The XML is still valid
2. Your specific changes are present
3. The file size is reasonable (not 0 bytes, not 100× the original)

```python
import xml.etree.ElementTree as ET
ET.parse('word/document.xml')  # raises if broken

# Confirm specific changes
with open('word/document.xml') as f:
    xml = f.read()
assert 'old_thing' not in xml
assert 'new_thing' in xml
```

---

## 14. Word Will Sometimes Re-Render Math on Open

Word's equation editor may re-layout math when the document opens. The XML may be "correct" but display differently than expected (e.g., subscripts move, fonts shift).

**Always ask the user to open the file and visually verify** the critical changes. Don't claim "done" until they confirm Word renders it correctly.

---

## 15. When in Doubt, Hand Back Content for Manual Insertion

Programmatic .docx editing is brittle. For complex insertions (multi-table nomenclatures, complex equation arrays), it's often safer to:

1. Generate the content as **plain markdown or HTML**
2. Hand it to the user
3. Let them paste into Word, which handles styling/formatting automatically

This sacrifices automation for reliability. For one-off edits, it's almost always the right tradeoff. For dozens of similar edits (a search-and-replace pass), the XML approach pays off.

---

## Quick-Reference Workflow Template

```python
import re
import xml.etree.ElementTree as ET
import shutil

# 1. BACKUP
shutil.copy('Original.docx', 'Original_BACKUP.docx')

# 2. EXTRACT
import zipfile
with zipfile.ZipFile('Original.docx') as z:
    z.extractall('/tmp/docx_work')

# 3. READ
with open('/tmp/docx_work/word/document.xml') as f:
    xml = f.read()

# 4. EDIT (position-based, end-to-start, with context checks)
positions = [(m.start(), m.end()) for m in re.finditer(r'<m:t>X</m:t>', xml)]
to_replace = [(s, e) for (s, e) in positions if some_context_check(xml, e)]
for s, e in reversed(to_replace):
    xml = xml[:s] + '<m:t>Y</m:t>' + xml[e:]

# 5. WRITE
with open('/tmp/docx_work/word/document.xml', 'w') as f:
    f.write(xml)

# 6. VALIDATE
ET.parse('/tmp/docx_work/word/document.xml')  # raises if broken

# 7. REPACKAGE
import os
os.chdir('/tmp/docx_work')
os.system('zip -r -q /tmp/output.docx . -x ".DS_Store"')

# 8. REPLACE
shutil.move('/tmp/output.docx', 'Original.docx')

# 9. ASK USER TO VERIFY IN WORD
```

---

## Top Five Reminders, in Priority Order

1. **Backup first, every time, before each edit pass.**
2. **Never use greedy regex with `re.DOTALL` across `<m:sSub>` or `<m:sSup>` boundaries.** Use position-based replacement.
3. **Validate XML after every batch of edits**, not just at the end.
4. **Disambiguate symbols by context** (next `<m:t>` text, surrounding structure).
5. **Always ask the user to open Word and visually verify** before claiming done.
