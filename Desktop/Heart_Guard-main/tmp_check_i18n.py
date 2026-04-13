import re
import glob

html_files = glob.glob('app/templates/**/*.html', recursive=True)
keys = set()
for fn in html_files:
    with open(fn, encoding='utf-8') as f:
        txt = f.read()
    for m in re.finditer(r'data-i18n(?:-title|-placeholder)?="([^"]+)"', txt):
        keys.add(m.group(1))

with open('app/static/js/language.js', encoding='utf-8') as f:
    js = f.read()
js_keys = set(re.findall(r"'([a-zA-Z0-9_]+)':", js))
missing = sorted(k for k in keys if k not in js_keys)
print('TEMPLATE_KEYS', len(keys))
print('JS_KEYS', len(js_keys))
print('MISSING', len(missing))
for k in missing:
    print(k)
