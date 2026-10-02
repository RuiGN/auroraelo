/* Envia o formulário de idioma ao escolher uma opção (a CSP não permite onchange inline). */
(function () {
  'use strict';
  Array.prototype.forEach.call(document.querySelectorAll('[data-ae-language-form] select'), function (select) {
    select.addEventListener('change', function () {
      if (select.form) select.form.submit();
    });
  });
})();
