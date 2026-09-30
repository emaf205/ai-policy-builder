from pathlib import Path
from playwright.sync_api import sync_playwright
from zipfile import ZipFile
from lxml import etree
import fitz,re
ROOT=Path(__file__).resolve().parents[1]
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for w,h in [(1440,900),(390,844),(360,780)]:
  page=browser.new_page(viewport={'width':w,'height':h},accept_downloads=True,reduced_motion='reduce')
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content((ROOT/'index.html').read_text(encoding='utf8'),wait_until='load')
  page.screenshot(path=str(ROOT/'screenshots'/f'landing-{w}.png'),full_page=True)
  assert page.locator('#hero-title').inner_text()=='AI Policy Builder.'
  assert page.locator('.hero-photo').evaluate('(el)=>el.complete && el.naturalWidth>500')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),f'overflow landing {w}'
  page.locator('#start').click()
  assert not page.locator('#flow').is_hidden()
  page.locator('#company').fill('Studio Prova & Associati S.r.l.')
  page.locator('#sector').select_option(label='Servizi professionali')
  page.locator('#employees').fill('53')
  page.screenshot(path=str(ROOT/'screenshots'/f'form-{w}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),f'overflow form {w}'
  page.locator('#next').click()
  assert page.locator('#step-label').inner_text()=='02 / 03'
  page.locator('input[name="toolchoices"]').first.check()
  page.locator('input[name="uses"]').first.check()
  page.locator('input[name="datalevel"][value="internal"]').check()
  page.locator('input[name="critical"][value="contracts"]').check()
  page.locator('#next').click()
  assert page.locator('#step-label').inner_text()=='03 / 03'
  page.locator('#owner').fill('Direzione')
  page.locator('#contact').fill('Ufficio IT')
  page.locator('#reviewer').fill('Responsabile del processo')
  page.locator('#generate').click()
  assert not page.locator('#result').is_hidden()
  result=page.locator('#document').inner_text()
  assert 'Studio Prova & Associati S.r.l.' in result and 'BOZZA NON APPROVATA' in result
  assert 'contratt' in result.lower()
  page.screenshot(path=str(ROOT/'screenshots'/f'result-{w}.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),f'overflow result {w}'
  page.locator('#tabEdit').click()
  page.locator('#editor').fill(page.locator('#editor').input_value()+'\n\n## Sezione approvata per test\nControllo personalizzato.')
  page.locator('#tabPreview').click()
  assert 'Controllo personalizzato' in page.locator('#document').inner_text()
  if w==1440:
   for id,ext in [('saveDocx','.docx'),('saveMd','.md'),('saveTxt','.txt'),('saveHtml','.html'),('saveEmail','.eml')]:
    with page.expect_download() as d:page.locator('#'+id).click()
    out=ROOT/'screenshots'/('export-sample'+ext)
    d.value.save_as(str(out))
    assert out.stat().st_size>100
    if ext=='.docx':
     with ZipFile(out) as z:
      assert z.testzip() is None
      xml=z.read('word/document.xml');etree.fromstring(xml)
      assert b'Sezione approvata per test' in xml
    if ext=='.md': assert 'Controllo personalizzato' in out.read_text()
   page.pdf(path=str(ROOT/'screenshots'/'print.pdf'),format='A4',print_background=True)
   pdf=fitz.open(str(ROOT/'screenshots'/'print.pdf'))
   text='\n'.join(p.get_text() for p in pdf)
   assert 'BOZZA NON APPROVATA' in text and 'Controllo personalizzato.' in text
   assert 2<=len(pdf)<=15
   print('A4_PDF_PAGES',len(pdf))
  page.close()
 browser.close()
assert not errors,errors
print('FLOW_1440_390_360_PASS')
print('EXPORT_DOCX_MD_TXT_HTML_EML_PASS')
print('PRINT_A4_PASS')
print('PAGE_ERRORS_NONE')
