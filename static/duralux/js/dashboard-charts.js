(() => {
  "use strict";

  const initializeRegistrationChart = () => {
    const source = document.getElementById("registration-series");
    const container = document.getElementById("registrations-chart");
    if (!source || !container || !window.ApexCharts) return;

    let series;
    try {
      series = JSON.parse(source.textContent || "[]");
    } catch (_error) {
      return;
    }

    const documentLanguage = document.documentElement.lang || "pt-BR";
    const seriesName = container.getAttribute("data-series-label") || "";
    const noDataText = container.getAttribute("data-no-data-text") || "";

    const monthFormatter = new Intl.DateTimeFormat(documentLanguage, {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });

    const formatCategory = (label) => {
      const match = /^(\d{4})-(\d{2})$/.exec(label);
      if (!match) return label;
      const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, 1));
      return monthFormatter.format(date);
    };

    const categories = series.map((item) => formatCategory(item.label));

    const chart = new window.ApexCharts(container, {
      chart: { type: "bar", height: 240, toolbar: { show: false } },
      series: [{ name: seriesName, data: series.map((item) => item.count) }],
      xaxis: { categories },
      colors: [getComputedStyle(document.documentElement).getPropertyValue("--product-primary").trim()],
      noData: { text: noDataText },
    });
    chart.render();
  };

  document.addEventListener("DOMContentLoaded", initializeRegistrationChart);
})();
