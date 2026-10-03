import glob
import re

templates = glob.glob("psychiatry/templates/psychiatry/*.html")
html_to_inject = """  <div class="p-3 rounded-xl bg-light-subtle border mb-4">
    <h2 class="h5 text-dark mb-2">{% translate "Indisponível nesta interface" %}</h2>
    <p class="fs-13 text-muted mb-2">{% translate "O acionamento de SOS pelo portal está indisponível. Não há plantão, monitoramento ou envio de ajuda por esta página." %}</p>
    <p class="fs-12 text-muted mb-0">{% translate "Esta página não grava dados nem envia notificações." %}</p>
  </div>
"""

for filepath in templates:
    if "base_aurora.html" in filepath:
        continue
    with open(filepath, "r") as f:
        content = f.read()
    
    # Remove the script block if it exists
    script_pattern = re.compile(r"<script>\s*document\.addEventListener.*?<\/script>\s*", re.DOTALL)
    content = script_pattern.sub("", content)

    # Now inject the HTML block right after {% block content %}
    if "{% block content %}" in content and html_to_inject.strip() not in content:
        content = content.replace("{% block content %}", "{% block content %}\n" + html_to_inject)

    with open(filepath, "w") as f:
        f.write(content)
