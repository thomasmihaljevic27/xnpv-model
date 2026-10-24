from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from lxml import etree as E
import hashlib, shutil, json

root = Path('C:/Users/Thomas/Desktop/xNPV')
qa = root/'30_OUTPUT/formatting_qa'
ref = root/'40_DOCS/Supervisor_Drafts/Data, Production, and Aging.docx'
targets = [root/'40_DOCS/Supervisor_Drafts/Circularity and Game Value.docx'] + [root/'40_DOCS'/s for s in ['Doc_3_Player_Pillar_II.docx','Doc_4_Drafting_Prospects_Unbuilt.docx','Doc_5_Cross_Cutting.docx']]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns = {'w': W}
def q(s): return '{'+W+'}'+s
def xml(b): return E.fromstring(b)
def serial(e): return E.tostring(e, xml_declaration=True, encoding='UTF-8', standalone=True)
with ZipFile(ref) as z: source = {s:z.read(s) for s in z.namelist()}
refhash = hashlib.sha256(ref.read_bytes()).hexdigest()
styles = xml(source['word/styles.xml'])
doc = xml(source['word/document.xml'])
roles = {}
for p in doc.xpath('//w:body/w:p',namespaces=ns):
    role = p.xpath('./w:pPr/w:pStyle/@w:val',namespaces=ns)
    roles.setdefault(role[0] if role else 'Normal',deepcopy(p.find(q('pPr'))))
font = deepcopy(doc.xpath('//w:rPr/w:rFonts',namespaces=ns)[0])
(qa/'artifact.md').write_text(f'''Reference: {ref}\nSHA256: {refhash}\nUS Letter, one-inch margins, header/footer 708 twips. One section, no tables or page furniture.\nCalibri theme minor font. Normal 11 pt black, 10 pt after, 1.15 line spacing. Title 15 pt bold black, 12 pt after. Heading1 13 pt bold #2E74B5, 14 pt before/7 pt after; Heading2 12 pt bold #1F4D78, 10 pt before/7 pt after.\nCopy source styles, theme, role paragraph properties and run font. Target top-level Heading2 maps to Heading1. Preserve all wording, emphasis, fields, relationships and other package parts. Preserve original files in dated archive.\nVisual reference audit blocked: packaged renderer requires absent LibreOffice. Page count unresolved.\n''',encoding='utf-8')
report=[]
for path in targets:
    backup = root/'90_ARCHIVE/2026-09-11/formatting_before'/path.relative_to(root/'40_DOCS')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists(): shutil.copy2(path,backup)
    with ZipFile(path) as z: parts={s:z.read(s) for s in z.namelist()}
    original=dict(parts)
    tree=xml(parts['word/document.xml'])
    text_before=tree.xpath('//w:t/text()',namespaces=ns)
    for p in tree.xpath('//w:body/w:p',namespaces=ns):
        old=p.find(q('pPr'))
        sid=p.xpath('./w:pPr/w:pStyle/@w:val',namespaces=ns)
        role='Title' if sid==['Title'] else 'Heading1' if sid and sid[0].startswith('Heading') else 'Normal'
        new=deepcopy(roles[role])
        if old is not None:
            for tag in ['numPr','sectPr']:
                value=old.find(q(tag))
                if value is not None: new.append(deepcopy(value))
            p.remove(old)
        p.insert(0,new)
        for r in p.xpath('.//w:r',namespaces=ns):
            rp=r.find(q('rPr'))
            if rp is None: rp=E.Element(q('rPr'));r.insert(0,rp)
            remove=['rFonts','sz','szCs','color','spacing','position','w','rStyle']
            if role!='Normal': remove+=['b','bCs','i','iCs']
            for child in list(rp):
                if E.QName(child).localname in remove: rp.remove(child)
            rp.insert(0,deepcopy(font))
    for sect in tree.xpath('//w:sectPr',namespaces=ns):
        for tag in ['pgSz','pgMar','cols','docGrid']:
            old=sect.find(q(tag))
            if old is not None: sect.remove(old)
            val=doc.find('.//'+q('sectPr')+'/'+q(tag))
            if val is not None: sect.append(deepcopy(val))
    targetstyles=xml(parts['word/styles.xml'])
    for s in styles:
        sid=s.get(q('styleId'))
        for old in list(targetstyles):
            if (sid and old.get(q('styleId'))==sid) or (not sid and old.tag==s.tag): targetstyles.remove(old)
        targetstyles.append(deepcopy(s))
    parts['word/styles.xml']=serial(targetstyles)
    parts['word/theme/theme1.xml']=source['word/theme/theme1.xml']
    parts['word/document.xml']=serial(tree)
    assert text_before==tree.xpath('//w:t/text()',namespaces=ns)
    changed=[s for s in parts if parts[s]!=original.get(s)]
    assert set(changed)<= {'word/document.xml','word/styles.xml','word/theme/theme1.xml'}
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for s,b in parts.items(): z.writestr(s,b)
    report.append({'file':str(path),'text_nodes_preserved':len(text_before),'changed_parts':changed})
assert refhash==hashlib.sha256(ref.read_bytes()).hexdigest()
(qa/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
