from pathlib import Path
from playwright.sync_api import sync_playwright
from zipfile import ZipFile
from lxml import etree
import fitz

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / 'index.html').read_text(encoding='utf8')
APP_URL = 'https://emaf205.com/ideas/ai-policy-builder/'
errors = []
OUT = ROOT / 'screenshots'
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    for w, h in [(1440, 900), (390, 844), (360, 780)]:
        page = browser.new_page(viewport={'width': w, 'height': h}, accept_downloads=True, reduced_motion='reduce')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.set_content(HTML, wait_until='load')

        assert page.locator('header.header').count() == 0
        assert page.locator('#startExample').is_visible()
        assert page.locator('.outcome-preview').is_visible()
        assert page.locator('link[rel="canonical"]').get_attribute('href') == APP_URL
        assert page.locator('meta[property="og:url"]').get_attribute('content') == APP_URL
        assert f"const APP_URL='{APP_URL}'" in HTML
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')

        page.locator('#startExample').click()
        page.locator('#company').fill('Studio Prova & Associati S.r.l.')
        page.locator('#sector').select_option(label='Servizi professionali')
        page.locator('#employees').fill('53')
        page.locator('#next').click()
        page.locator('input[name="toolchoices"]').first.check()
        page.locator('input[name="uses"]').first.check()
        page.locator('input[name="datalevel"][value="internal"]').check()
        page.locator('input[name="critical"][value="contracts"]').check()
        page.locator('#next').click()
        page.locator('#owner').fill('Direzione')
        page.locator('#contact').fill('Ufficio IT')
        page.locator('#reviewer').fill('Responsabile del processo')
        page.locator('#generate').click()

        assert not page.locator('#result').is_hidden()
        assert page.locator('.author-cta').is_visible()
        assert page.locator('.closing-cta').is_visible()
        result = page.locator('#document').inner_text()
        assert 'Studio Prova & Associati S.r.l.' in result
        assert 'BOZZA NON APPROVATA' in result
        assert 'contratt' in result.lower()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')

        page.locator('#tabEdit').click()
        page.locator('#editor').fill(page.locator('#editor').input_value() + '\n\n## Sezione approvata per test\nControllo personalizzato.')
        page.locator('#tabPreview').click()
        assert 'Controllo personalizzato' in page.locator('#document').inner_text()

        if w == 1440:
            for id_, ext in [('saveDocx', '.docx'), ('saveMd', '.md'), ('saveTxt', '.txt'), ('saveHtml', '.html'), ('saveEmail', '.eml')]:
                with page.expect_download() as d:
                    page.locator('#' + id_).click()
                out = OUT / ('export-sample' + ext)
                d.value.save_as(str(out))
                assert out.stat().st_size > 100
                if ext == '.docx':
                    with ZipFile(out) as z:
                        assert z.testzip() is None
                        xml = z.read('word/document.xml')
                        etree.fromstring(xml)
                        assert b'Sezione approvata per test' in xml
                if ext == '.md':
                    assert 'Controllo personalizzato' in out.read_text()

            page.pdf(path=str(OUT / 'print.pdf'), format='A4', print_background=True)
            pdf = fitz.open(str(OUT / 'print.pdf'))
            text = '\n'.join(pg.get_text() for pg in pdf)
            assert 'BOZZA NON APPROVATA' in text
            assert 'Controllo personalizzato.' in text
            assert 2 <= len(pdf) <= 15

        page.close()
    browser.close()

assert not errors, errors
print('V8.1_SMOKE_PASS')
