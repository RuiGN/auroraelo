/**
 * Aurora Elo Design System - Input Mask Engine
 * Handles automatic input formatting for Brazilian & International healthcare inputs.
 */

const AuroraMasks = {
  // CPF Mask: 000.000.000-00
  cpf(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 11);
    return digits
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  },

  // Phone Mask: (00) 00000-0000 or (00) 0000-0000
  phone(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 11);
    if (digits.length <= 10) {
      return digits
        .replace(/(\d{2})(\d)/, '($1) $2')
        .replace(/(\d{4})(\d)/, '$1-$2');
    }
    return digits
      .replace(/(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{5})(\d{4})$/, '$1-$2');
  },

  // Date Mask: DD/MM/YYYY
  date(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 8);
    return digits
      .replace(/(\d{2})(\d)/, '$1/$2')
      .replace(/(\d{2})(\d)/, '$1/$2');
  },

  // Time Mask: HH:MM
  time(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 4);
    return digits.replace(/(\d{2})(\d)/, '$1:$2');
  },

  // Currency Mask (BRL / USD adaptable)
  currency(value, currencySymbol = 'R$') {
    if (!value) return `${currencySymbol} 0,00`;
    let digits = value.replace(/\D/g, '');
    if (!digits) return `${currencySymbol} 0,00`;
    let num = (parseInt(digits, 10) / 100).toFixed(2);
    let parts = num.split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return `${currencySymbol} ${parts.join(',')}`;
  },

  // CEP Mask: 00000-000
  cep(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 8);
    return digits.replace(/(\d{5})(\d)/, '$1-$2');
  },

  // CRM Mask: CRM/UF 000000
  crm(value) {
    if (!value) return '';
    const cleaned = value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    const ufs = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'];
    
    // Check if starts with CRM
    let uf = 'SP';
    let digits = value.replace(/\D/g, '').slice(0, 6);
    return digits ? `CRM-${digits}` : '';
  },

  // Medical Record No (Prontuário): PRON-YYYY-0000
  recordNo(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 4) return digits;
    return `PRON-${digits.slice(0, 4)}-${digits.slice(4)}`;
  },

  // CNS (Cartão Nacional de Saúde): 000 0000 0000 0000
  cns(value) {
    if (!value) return '';
    const digits = value.replace(/\D/g, '').slice(0, 15);
    return digits
      .replace(/(\d{3})(\d)/, '$1 $2')
      .replace(/(\d{4})(\d)/, '$1 $2')
      .replace(/(\d{4})(\d)/, '$1 $2');
  },

  // Initialize masks on elements with data-mask attributes
  init() {
    document.querySelectorAll('[data-mask]').forEach((input) => {
      const maskType = input.getAttribute('data-mask');

      const apply = () => {
        const val = input.value;
        switch (maskType) {
          case 'cpf':
            input.value = AuroraMasks.cpf(val);
            break;
          case 'phone':
            input.value = AuroraMasks.phone(val);
            break;
          case 'date':
            input.value = AuroraMasks.date(val);
            break;
          case 'time':
            input.value = AuroraMasks.time(val);
            break;
          case 'currency':
            input.value = AuroraMasks.currency(val);
            break;
          case 'cep':
            input.value = AuroraMasks.cep(val);
            break;
          case 'record':
            input.value = AuroraMasks.recordNo(val);
            break;
          case 'cns':
            input.value = AuroraMasks.cns(val);
            break;
        }
      };

      input.addEventListener('input', apply);
      input.addEventListener('blur', apply);
    });

    // 2FA OTP auto-advance setup
    const otpContainers = document.querySelectorAll('.otp-inputs-group');
    otpContainers.forEach(container => {
      const inputs = container.querySelectorAll('input');
      inputs.forEach((input, idx) => {
        input.addEventListener('input', (e) => {
          if (input.value.length === 1 && idx < inputs.length - 1) {
            inputs[idx + 1].focus();
          }
        });
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Backspace' && !input.value && idx > 0) {
            inputs[idx - 1].focus();
          }
        });
      });
    });
  }
};

if (typeof window !== 'undefined') {
  window.AuroraMasks = AuroraMasks;
}
