/**
 * Aurora Elo Design System - Interactive Application Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize i18n
  if (window.AuroraI18n) {
    window.AuroraI18n.init();
  }

  // Initialize Input Masks
  if (window.AuroraMasks) {
    window.AuroraMasks.init();
  }

  // Tab Navigation Handling
  const tabBtns = document.querySelectorAll('.ds-tab-btn');
  const tabSections = document.querySelectorAll('.ds-tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      // Update button active styles
      tabBtns.forEach(b => {
        b.classList.remove('border-aurora-600', 'text-aurora-600', 'bg-aurora-50', 'dark:bg-aurora-900/50', 'dark:text-aurora-400');
        b.classList.add('border-transparent', 'text-slate-600', 'dark:text-slate-400', 'hover:text-aurora-600');
      });

      btn.classList.remove('border-transparent', 'text-slate-600', 'dark:text-slate-400');
      btn.classList.add('border-aurora-600', 'text-aurora-600', 'bg-aurora-50', 'dark:bg-aurora-900/50', 'dark:text-aurora-400');

      // Show targeted tab section
      tabSections.forEach(sec => {
        if (sec.id === targetTab) {
          sec.classList.remove('hidden');
        } else {
          sec.classList.add('hidden');
        }
      });

      // Scroll to top of tab container
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });

  // Layout Switcher (Vertical vs Horizontal Nav in Showcase)
  const btnLayoutVertical = document.getElementById('btn-layout-vertical');
  const btnLayoutHorizontal = document.getElementById('btn-layout-horizontal');
  const showcaseShell = document.getElementById('showcase-main-shell');
  const verticalSidebar = document.getElementById('showcase-vertical-sidebar');
  const horizontalNavbar = document.getElementById('showcase-horizontal-navbar');

  function setLayoutMode(mode) {
    if (mode === 'horizontal') {
      if (verticalSidebar) verticalSidebar.classList.add('hidden');
      if (horizontalNavbar) horizontalNavbar.classList.remove('hidden');
      if (btnLayoutHorizontal) {
        btnLayoutHorizontal.classList.add('bg-white', 'text-aurora-900', 'shadow-sm');
        btnLayoutHorizontal.classList.remove('text-slate-600');
      }
      if (btnLayoutVertical) {
        btnLayoutVertical.classList.remove('bg-white', 'text-aurora-900', 'shadow-sm');
        btnLayoutVertical.classList.add('text-slate-600');
      }
    } else {
      if (verticalSidebar) verticalSidebar.classList.remove('hidden');
      if (horizontalNavbar) horizontalNavbar.classList.add('hidden');
      if (btnLayoutVertical) {
        btnLayoutVertical.classList.add('bg-white', 'text-aurora-900', 'shadow-sm');
        btnLayoutVertical.classList.remove('text-slate-600');
      }
      if (btnLayoutHorizontal) {
        btnLayoutHorizontal.classList.remove('bg-white', 'text-aurora-900', 'shadow-sm');
        btnLayoutHorizontal.classList.add('text-slate-600');
      }
    }
  }

  if (btnLayoutVertical) btnLayoutVertical.addEventListener('click', () => setLayoutMode('vertical'));
  if (btnLayoutHorizontal) btnLayoutHorizontal.addEventListener('click', () => setLayoutMode('horizontal'));

  // Language Selector
  const langSelects = document.querySelectorAll('.aurora-lang-select');
  langSelects.forEach(select => {
    select.value = window.AuroraI18n ? window.AuroraI18n.currentLang : 'pt-BR';
    select.addEventListener('change', (e) => {
      if (window.AuroraI18n) {
        window.AuroraI18n.setLanguage(e.target.value);
        langSelects.forEach(s => s.value = e.target.value);
        showToast(`Idioma alterado para: ${select.options[select.selectedIndex].text}`);
      }
    });
  });

  // Dark Mode Toggle
  const themeToggles = document.querySelectorAll('.aurora-theme-toggle');
  themeToggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
      const isDark = document.documentElement.classList.contains('dark');
      localStorage.setItem('aurora_theme', isDark ? 'dark' : 'light');
      showToast(isDark ? 'Modo Escuro Ativado' : 'Modo Claro Ativado');
    });
  });

  if (localStorage.getItem('aurora_theme') === 'dark') {
    document.documentElement.classList.add('dark');
  }

  // Password Visibility Toggle
  const togglePassBtns = document.querySelectorAll('.toggle-password-visibility');
  togglePassBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (input && input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = `
          <svg class="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18"></path>
          </svg>`;
      } else if (input) {
        input.type = 'password';
        btn.innerHTML = `
          <svg class="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
          </svg>`;
      }
    });
  });

  // Password Strength Meter
  const passInputs = document.querySelectorAll('.input-password-strength');
  passInputs.forEach(input => {
    const bar = document.querySelector('.password-strength-bar');
    const label = document.querySelector('.password-strength-label');
    if (!bar || !label) return;

    input.addEventListener('input', () => {
      const val = input.value;
      let score = 0;
      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      if (val.length === 0) {
        bar.style.width = '0%';
        bar.className = 'password-strength-bar h-1.5 rounded-full transition-all duration-300 bg-slate-200';
        label.textContent = '';
      } else if (score <= 1) {
        bar.style.width = '25%';
        bar.className = 'password-strength-bar h-1.5 rounded-full transition-all duration-300 bg-crisis-500';
        label.textContent = 'Senha Fraca';
        label.className = 'password-strength-label text-xs font-medium text-crisis-600';
      } else if (score === 2) {
        bar.style.width = '50%';
        bar.className = 'password-strength-bar h-1.5 rounded-full transition-all duration-300 bg-alert-500';
        label.textContent = 'Senha Média';
        label.className = 'password-strength-label text-xs font-medium text-alert-600';
      } else if (score === 3) {
        bar.style.width = '75%';
        bar.className = 'password-strength-bar h-1.5 rounded-full transition-all duration-300 bg-elo-500';
        label.textContent = 'Senha Boa';
        label.className = 'password-strength-label text-xs font-medium text-elo-600';
      } else {
        bar.style.width = '100%';
        bar.className = 'password-strength-bar h-1.5 rounded-full transition-all duration-300 bg-healing-500';
        label.textContent = 'Senha Forte & Segura';
        label.className = 'password-strength-label text-xs font-medium text-healing-600';
      }
    });
  });

  // Range Slider Feedback
  const anxietySlider = document.getElementById('anxiety-scale-slider');
  const anxietyValDisplay = document.getElementById('anxiety-scale-val');
  if (anxietySlider && anxietyValDisplay) {
    const updateSlider = () => {
      const v = anxietySlider.value;
      let desc = 'Mínima / Calmo';
      let colorClass = 'text-healing-600 bg-healing-50';
      if (v >= 3 && v <= 5) {
        desc = 'Leve a Moderada';
        colorClass = 'text-aurora-600 bg-aurora-50';
      } else if (v >= 6 && v <= 8) {
        desc = 'Moderada a Severa';
        colorClass = 'text-alert-600 bg-alert-50';
      } else if (v >= 9) {
        desc = 'Crise Aguda / Pânico';
        colorClass = 'text-crisis-600 bg-crisis-50';
      }
      anxietyValDisplay.innerHTML = `<span class="px-2.5 py-1 rounded-full text-xs font-bold ${colorClass}">${v}/10 • ${desc}</span>`;
    };
    anxietySlider.addEventListener('input', updateSlider);
    updateSlider();
  }

  // Textarea Character Counter
  const notesTextarea = document.getElementById('clinical-notes-textarea');
  const notesCounter = document.getElementById('notes-char-counter');
  if (notesTextarea && notesCounter) {
    notesTextarea.addEventListener('input', () => {
      const count = notesTextarea.value.length;
      notesCounter.textContent = `${count} / 1000`;
    });
  }

  // Patient Table Search & Filtering
  const tableSearchInput = document.getElementById('table-patient-search');
  const tableStatusFilter = document.getElementById('table-filter-status');
  const tableRiskFilter = document.getElementById('table-filter-risk');
  const tableRows = document.querySelectorAll('.patient-row');

  function filterPatientTable() {
    const query = tableSearchInput ? tableSearchInput.value.toLowerCase().trim() : '';
    const status = tableStatusFilter ? tableStatusFilter.value : 'all';
    const risk = tableRiskFilter ? tableRiskFilter.value : 'all';

    tableRows.forEach(row => {
      const text = row.innerText.toLowerCase();
      const rowStatus = row.getAttribute('data-status');
      const rowRisk = row.getAttribute('data-risk');

      const matchesQuery = !query || text.includes(query);
      const matchesStatus = status === 'all' || rowStatus === status;
      const matchesRisk = risk === 'all' || rowRisk === risk;

      if (matchesQuery && matchesStatus && matchesRisk) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  if (tableSearchInput) tableSearchInput.addEventListener('input', filterPatientTable);
  if (tableStatusFilter) tableStatusFilter.addEventListener('change', filterPatientTable);
  if (tableRiskFilter) tableRiskFilter.addEventListener('change', filterPatientTable);

  // File Dropzone Visual Feedback
  const dropzone = document.getElementById('form-file-dropzone');
  const dropFileInput = document.getElementById('form-file-input');
  const dropFileList = document.getElementById('form-file-list');

  if (dropzone && dropFileInput) {
    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.add('border-aurora-500', 'bg-aurora-50/50');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-aurora-500', 'bg-aurora-50/50');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      handleFiles(files);
    });

    dropFileInput.addEventListener('change', () => {
      handleFiles(dropFileInput.files);
    });

    function handleFiles(files) {
      if (!files || files.length === 0) return;
      if (dropFileList) {
        dropFileList.innerHTML = '';
        Array.from(files).forEach(file => {
          const item = document.createElement('div');
          item.className = 'flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs';
          item.innerHTML = `
            <div class="flex items-center space-x-2 truncate">
              <svg class="w-4 h-4 text-aurora-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              <span class="font-medium text-slate-700 truncate">${file.name}</span>
              <span class="text-slate-400 text-[10px]">(${(file.size / 1024).toFixed(1)} KB)</span>
            </div>
            <span class="text-healing-600 font-semibold flex items-center gap-1">✓ Pronto</span>
          `;
          dropFileList.appendChild(item);
        });
      }
      showToast(`${files.length} arquivo(s) anexado(s) com sucesso`);
    }
  }

  // Toast Notification Engine
  function showToast(msg, duration = 3000) {
    let toast = document.getElementById('aurora-global-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'aurora-global-toast';
      toast.className = 'fixed bottom-6 right-6 z-50 transform translate-y-20 opacity-0 transition-all duration-300 px-4 py-3 rounded-xl shadow-aurora-lg bg-aurora-900 text-white text-sm font-medium flex items-center space-x-3 border border-aurora-700';
      document.body.appendChild(toast);
    }
    toast.innerHTML = `
      <div class="w-2 h-2 rounded-full bg-elo-400 animate-pulse"></div>
      <span>${msg}</span>
    `;
    toast.classList.remove('translate-y-20', 'opacity-0');
    toast.classList.add('translate-y-0', 'opacity-100');

    setTimeout(() => {
      toast.classList.remove('translate-y-0', 'opacity-100');
      toast.classList.add('translate-y-20', 'opacity-0');
    }, duration);
  }
  window.showToast = showToast;

  // Global Code Copy Helper
  document.querySelectorAll('.btn-copy-code').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-code-target');
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        navigator.clipboard.writeText(targetEl.innerText);
        showToast('Código copiado para a área de transferência!');
      }
    });
  });
});
