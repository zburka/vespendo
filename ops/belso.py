"""Az n8n webhookok hívása a belső hálózatról (az n8n konténerből): kívülről a VeSpendo végpontok el vannak zárva.
`h(háztartás, metódus, útvonal, body, személy)` -> (200, json) siker esetén, (400, {}) hibás válasznál (a busybox wget nem adja ki a törzset)."""
import json, subprocess
from common import ENV


def h(hz, metodus, ut, body=None, szemely='anna'):
    cmd = ['docker', 'exec', 'n8n', 'wget', '-qO-', '--header', f"X-App-Key: {ENV['VESPENDO_APP_KEY']}", '--header', f'X-Szemely: {szemely}',
           '--header', 'Content-Type: application/json']
    if hz:
        cmd += ['--header', f'X-Haztartas: {hz}']
    if metodus == 'POST':
        cmd += ['--post-data', json.dumps(body if body is not None else {})]
    cmd.append(f'http://localhost:5678/webhook/{ut}')
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return 400, {}
    try:
        return 200, json.loads(r.stdout)
    except ValueError:
        return 200, {}
