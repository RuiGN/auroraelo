import os
import re

FILES = [
    "addiction_dashboard.html",
    "anamnesis.html",
    "beds.html",
    "crisis_protocol.html",
    "telepsychiatry_room.html",
    "twelve_steps_anamnesis.html"
]

DIR = "/Users/rgnsystems/Documents/auroraelo_v2/auroraelo/psychiatry/templates/psychiatry"

MESSAGE = """
  <div class="alert alert-warning m-4">
    <h4>Indisponível nesta interface</h4>
    <p>Esta página não grava dados nem envia notificações.</p>
  </div>
"""

for filename in FILES:
    path = os.path.join(DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "Indisponível nesta interface" not in content:
        # append after <main> or <main ...>
        if "<main" in content:
            content = re.sub(r'(<main[^>]*>)', r'\1\n' + MESSAGE, content, count=1)
        else:
            # fallback if there's no <main> tag
            content = MESSAGE + content
            
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed {filename}")
    else:
        print(f"Skipped {filename}")
