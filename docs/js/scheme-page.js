(function () {
  var i18n = window.YojanaI18n;
  var lang = localStorage.getItem("yojana-lang") || "en";
  var copyNode = document.getElementById("scheme-copy");
  var copy = copyNode ? JSON.parse(copyNode.textContent) : null;

  function t(key) {
    var pack = i18n.STRINGS[lang] || i18n.STRINGS.en;
    return pack[key] || i18n.STRINGS.en[key] || key;
  }

  function apply() {
    document.documentElement.lang = lang === "te" ? "te" : lang === "hi" ? "hi" : "en";
    document.querySelectorAll("[data-i18n]").forEach(function (node) {
      node.textContent = t(node.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-lang]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-lang") === lang ? "true" : "false");
    });
    if (!copy) return;
    document.querySelectorAll("[data-scheme]").forEach(function (node) {
      var key = node.getAttribute("data-scheme");
      var bag = copy[key] || {};
      var value = bag[lang] || bag.en || "";
      if (key === "benefitAmount") node.textContent = value || t("benefitUnknown");
      else node.textContent = value;
    });
    document.querySelectorAll("[data-scheme-block]").forEach(function (node) {
      var key = node.getAttribute("data-scheme-block");
      var bag = copy[key] || {};
      var value = bag[lang] || bag.en || "";
      node.textContent = "";
      var parts = String(value || "").split(/\n+/).map(function (part) { return part.trim(); }).filter(Boolean);
      if (!parts.length && key === "howToApply") parts = ["Steps were not listed on the official page."];
      parts.forEach(function (part) {
        var paragraph = document.createElement("p");
        paragraph.textContent = part;
        node.appendChild(paragraph);
      });
    });
    var docs = (copy.documents && ((copy.documents[lang] && copy.documents[lang].length && copy.documents[lang]) || copy.documents.en)) || [];
    var list = document.getElementById("document-list");
    if (list) {
      list.innerHTML = "";
      if (!docs.length) {
        var empty = document.createElement("li");
        empty.textContent = t("documentsMissing");
        list.appendChild(empty);
      } else {
        docs.forEach(function (doc) {
          var item = document.createElement("li");
          item.textContent = doc;
          list.appendChild(item);
        });
      }
    }
  }

  document.querySelectorAll("[data-lang]").forEach(function (button) {
    button.addEventListener("click", function () {
      lang = button.getAttribute("data-lang");
      localStorage.setItem("yojana-lang", lang);
      apply();
    });
  });
  apply();
})();
