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

# The message we added blindly at the beginning:
WRONG_MESSAGE = MESSAGE

for filename in FILES:
    path = os.path.join(DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Clean up the wrongly prepended message
    if content.startswith(WRONG_MESSAGE):
        content = content[len(WRONG_MESSAGE):]
    
    # 2. Inject it immediately inside {% block content %}
    if "Indisponível nesta interface" not in content:
        content = re.sub(r'({%\s*block\s+content\s*%})', r'\1' + MESSAGE, content, count=1)
        
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Fixed {filename}")
