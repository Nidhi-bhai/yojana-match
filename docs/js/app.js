(function () {
  var i18n = window.YojanaI18n;
  var matcher = window.YojanaMatch;
  var pdf = window.YojanaPdf;
  var lang = localStorage.getItem("yojana-lang") || "en";
  var catalog = [];
  var lastProfile = null;
  var lastMatches = [];
  var lastPossible = [];
  var paypalReady = false;
  var ORDER_KEY = "yojana-help-orders";

  function t(key) {
    var pack = i18n.STRINGS[lang] || i18n.STRINGS.en;
    return pack[key] || i18n.STRINGS.en[key] || key;
  }

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function textOf(bag) {
    if (!bag) return "";
    return bag[lang] || bag.en || "";
  }

  function stateLabel(name) {
    var table = (i18n.STATE_NAMES[lang] || {})[name];
    return table || name;
  }

  function applyChrome() {
    document.documentElement.lang = lang === "te" ? "te" : lang === "hi" ? "hi" : "en";
    document.querySelectorAll("[data-i18n]").forEach(function (node) {
      node.textContent = t(node.getAttribute("data-i18n"));
    });
    document.querySelectorAll("option[data-i18n]").forEach(function (node) {
      node.textContent = t(node.getAttribute("data-i18n"));
    });
    document.querySelectorAll("#state option[value]").forEach(function (node) {
      if (!node.value) {
        node.textContent = t("choose");
        return;
      }
      var label = stateLabel(node.value);
      if (node.getAttribute("data-central-only") === "true") {
        label += " (" + t("centralOnly") + ")";
      }
      node.textContent = label;
    });
    document.querySelectorAll("[data-lang]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-lang") === lang ? "true" : "false");
    });
    document.querySelectorAll(".te-note").forEach(function (node) {
      node.hidden = lang !== "te";
    });
    var search = document.getElementById("result-search");
    if (search) search.placeholder = t("searchResults");
  }

  function readProfile(form) {
    var data = new FormData(form);
    var age = Number(data.get("age"));
    var groups = data.getAll("group");
    var profile = {
      state: data.get("state") || "",
      age: age,
      gender: data.get("gender") || "",
      incomeBand: data.get("income") || "",
      occupation: data.get("occupation") || "",
      caste: data.get("caste") || "",
      disability: data.get("disability") === "yes",
      residence: data.get("residence") || "",
      groups: groups,
      listing: data.get("listing") || "",
    };
    var missing =
      !profile.state ||
      !profile.gender ||
      !profile.incomeBand ||
      !profile.occupation ||
      !profile.caste ||
      !profile.residence ||
      !profile.listing ||
      !Number.isFinite(age) ||
      age < 0 ||
      age > 120;
    return { profile: profile, missing: missing };
  }

  function loadOrders() {
    try {
      var parsed = JSON.parse(localStorage.getItem(ORDER_KEY) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function saveOrder(entry) {
    var orders = loadOrders().filter(function (item) {
      return item.orderID !== entry.orderID;
    });
    orders.unshift(entry);
    localStorage.setItem(ORDER_KEY, JSON.stringify(orders.slice(0, 8)));
  }

  function checksFor(result) {
    return (result.checks || [])
      .map(function (check) {
        if (check.code === "broad") return t("checkBroad");
        if (check.code === "listing" || check.code === "listing-detail") return t("checkListing");
        if (check.code === "income-check") return t("checkIncome");
        if (check.quote) return t("checkQuote") + " " + check.quote;
        return "";
      })
      .filter(Boolean);
  }

  function card(scheme, kind) {
    var result = matcher.explain(scheme, lastProfile);
    var name = textOf(scheme.name);
    var benefit = scheme.benefitAmount || t("benefitUnknown");
    var eligibility = textOf(scheme.eligibility);
    if (eligibility.length > 500) eligibility = eligibility.slice(0, 500) + "…";
    var docs = scheme.documents && (scheme.documents[lang] || []).length
      ? scheme.documents[lang]
      : (scheme.documents && scheme.documents.en) || [];
    var apply = (scheme.applyLinks || [])[0];
    var href = "schemes/" + encodeURIComponent(scheme.slug) + "/";
    var badges =
      '<span class="badge">' + esc(t(scheme.level) || scheme.level) + "</span>" +
      (scheme.states || [])
        .filter(function (state) { return state !== "All"; })
        .slice(0, 2)
        .map(function (state) { return '<span class="badge clay">' + esc(stateLabel(state)) + "</span>"; })
        .join("");
    if (matcher.isClosed(scheme)) {
      badges += '<span class="badge closed">' + esc(t("closedBadge")) + "</span>";
    }
    var docHtml = docs.length
      ? "<ul class=\"doc-list\">" + docs.slice(0, 4).map(function (doc) { return "<li>" + esc(doc) + "</li>"; }).join("") + "</ul>"
      : "<p class=\"meta\">" + esc(t("documentsMissing")) + "</p>";
    var noteSource = kind === "possible" ? checksFor(result) : [];
    var noteHtml = noteSource.slice(0, 3).map(function (note) {
      return "<p class=\"note\">" + esc(note) + "</p>";
    }).join("");
    var applyHtml = apply
      ? '<a class="button" href="' + esc(apply.url) + '" rel="noopener noreferrer">' + esc(t("apply")) + "</a>"
      : "<span class=\"meta\">" + esc(t("applyMissing")) + "</span>";
    return (
      '<article class="card" data-level="' + esc(scheme.level) + '" data-name="' + esc(name.toLowerCase()) + '">' +
      "<header><div>" +
      '<div class="badges">' + badges + "</div>" +
      "<h3><a href=\"" + href + "\">" + esc(name) + "</a></h3>" +
      "</div></header>" +
      "<p class=\"benefit\">" + esc(benefit) + "</p>" +
      noteHtml +
      "<h4>" + esc(t("eligibility")) + "</h4>" +
      "<p>" + esc(eligibility || "—") + "</p>" +
      "<h4>" + esc(t("documents")) + "</h4>" +
      docHtml +
      "<p class=\"meta\">" + esc(t("verified")) + " " + esc(scheme.lastVerified) + "</p>" +
      '<div class="actions">' +
      applyHtml +
      '<a class="button secondary" href="' + href + '">' + esc(t("viewDetails")) + "</a>" +
      '<a class="button secondary" href="' + esc(scheme.sourceUrl) + '" rel="noopener noreferrer">' + esc(t("source")) + "</a>" +
      "</div></article>"
    );
  }

  function visible(rows) {
    var query = (document.getElementById("result-search").value || "").trim().toLowerCase();
    var filter = document.getElementById("result-filter").value;
    return rows.filter(function (scheme) {
      var name = textOf(scheme.name).toLowerCase();
      if (query && name.indexOf(query) === -1 && scheme.slug.indexOf(query) === -1) return false;
      if (filter === "central") return scheme.level === "Central";
      if (filter === "state") return scheme.level !== "Central";
      return true;
    });
  }

  function groupHtml(rows, kind) {
    var stateRows = rows.filter(function (scheme) { return scheme.level !== "Central"; });
    var centralRows = rows.filter(function (scheme) { return scheme.level === "Central"; });
    var html = "";
    if (stateRows.length) {
      html += "<h3 class=\"group-title\">" + esc(t("groupState")) + "</h3><div class=\"card-list\">" +
        stateRows.map(function (scheme) { return card(scheme, kind); }).join("") + "</div>";
    }
    if (centralRows.length) {
      html += "<h3 class=\"group-title\">" + esc(t("groupCentral")) + "</h3><div class=\"card-list\">" +
        centralRows.map(function (scheme) { return card(scheme, kind); }).join("") + "</div>";
    }
    return html;
  }

  function renderResults() {
    var root = document.getElementById("results");
    var matches = visible(lastMatches);
    var possible = visible(lastPossible);
    var html = '<div class="results-head"><h2>' + esc(t("resultsTitle")) + "</h2><p><strong>" +
      matches.length + "</strong> " + esc(t("matchCount")) + "</p></div>";
    if (!matches.length) {
      html += '<p class="empty">' + esc(t("noResults")) + "</p>";
    } else {
      html += groupHtml(matches, "match");
    }
    html += '<div class="results-head"><h2>' + esc(t("possibleTitle")) + "</h2><p><strong>" +
      possible.length + "</strong> " + esc(t("possibleCount")) + "</p></div>";
    html += "<p class=\"meta\">" + esc(t("possibleIntro")) + "</p>";
    if (possible.length) html += groupHtml(possible, "possible");
    root.innerHTML = html;
  }

  function downloadOrder(order) {
    var matched = matcher.matchAll(catalog, order.profile);
    pdf.downloadPdf(
      pdf.buildChecklistPdf(order.profile, matched, order.orderID),
      "yojanamatch-application-help-pack.pdf"
    );
  }

  function renderSavedOrders() {
    var box = document.getElementById("saved-orders");
    if (!box) return;
    var orders = loadOrders();
    if (!orders.length) {
      box.innerHTML = "";
      return;
    }
    box.innerHTML = orders.map(function (order) {
      return '<p class="order-row"><span>' + esc(t("orderLabel")) + ": <strong>" + esc(order.orderID) +
        "</strong></span> <button type=\"button\" class=\"secondary\" data-order=\"" + esc(order.orderID) +
        "\">" + esc(t("downloadAgain")) + "</button></p>";
    }).join("");
    box.querySelectorAll("[data-order]").forEach(function (button) {
      button.addEventListener("click", function () {
        var id = button.getAttribute("data-order");
        var order = loadOrders().filter(function (item) { return item.orderID === id; })[0];
        if (order) downloadOrder(order);
      });
    });
  }

  function setupPaypal() {
    var slot = document.getElementById("paypal-button");
    var note = document.getElementById("paypal-note");
    slot.innerHTML = "";
    if (!lastProfile) {
      note.hidden = false;
      note.textContent = t("helpNeedsMatch");
      return;
    }
    if (!lastMatches.length) {
      note.hidden = false;
      note.textContent = t("helpNoFirm");
      return;
    }
    var config = window.YOJANA_CONFIG || {};
    var clientId = config.PAYPAL_CLIENT_ID || "";
    if (!clientId || clientId.indexOf("YOUR_") === 0) {
      note.hidden = false;
      note.textContent = t("paypalMissing");
      return;
    }
    note.hidden = true;
    var profile = lastProfile;
    var matched = lastMatches.slice();
    function render() {
      slot.innerHTML = "";
      window.paypal.Buttons({
        style: { layout: "vertical", shape: "rect", label: "pay" },
        createOrder: function (data, actions) {
          return actions.order.create({
            purchase_units: [{
              description: "YojanaMatch application help pack",
              amount: { currency_code: "USD", value: "2.00" },
            }],
          });
        },
        onApprove: function (data, actions) {
          return actions.order.capture().then(function () {
            var order = {
              orderID: data.orderID,
              profile: profile,
              savedAt: new Date().toISOString(),
            };
            saveOrder(order);
            renderSavedOrders();
            note.hidden = false;
            note.textContent = t("orderLabel") + ": " + data.orderID;
            pdf.downloadPdf(
              pdf.buildChecklistPdf(profile, matched, data.orderID),
              "yojanamatch-application-help-pack.pdf"
            );
          });
        },
        onCancel: function () {
          note.hidden = false;
          note.textContent = t("paypalCancel");
        },
        onError: function () {
          note.hidden = false;
          note.textContent = t("paypalError");
        },
      }).render("#paypal-button");
    }
    if (window.paypal && paypalReady) render();
    else {
      var existing = document.getElementById("paypal-sdk");
      if (existing) {
        existing.addEventListener("load", function () {
          paypalReady = true;
          render();
        }, { once: true });
        return;
      }
      var script = document.createElement("script");
      script.id = "paypal-sdk";
      script.src = "https://www.paypal.com/sdk/js?client-id=" + encodeURIComponent(clientId) + "&currency=USD";
      script.onload = function () {
        paypalReady = true;
        render();
      };
      document.head.appendChild(script);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    var parsed = readProfile(event.currentTarget);
    var error = document.getElementById("form-error");
    if (parsed.missing) {
      error.textContent = t("formError");
      return;
    }
    error.textContent = "";
    lastProfile = parsed.profile;
    lastMatches = matcher.matchAll(catalog, lastProfile);
    lastPossible = matcher.possibleAll(catalog, lastProfile);
    renderResults();
    setupPaypal();
    document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  document.querySelectorAll("[data-lang]").forEach(function (button) {
    button.addEventListener("click", function () {
      lang = button.getAttribute("data-lang");
      localStorage.setItem("yojana-lang", lang);
      applyChrome();
      if (lastProfile) {
        renderResults();
        setupPaypal();
      }
      renderSavedOrders();
    });
  });

  document.getElementById("matcher-form").addEventListener("submit", onSubmit);
  document.getElementById("result-search").addEventListener("input", function () {
    if (lastProfile) renderResults();
  });
  document.getElementById("result-filter").addEventListener("change", function () {
    if (lastProfile) renderResults();
  });

  applyChrome();
  fetch("data/schemes.json")
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      catalog = payload.schemes || [];
      document.getElementById("loading").hidden = true;
      renderSavedOrders();
    })
    .catch(function () {
      document.getElementById("loading").textContent = "The scheme database did not load.";
    });
})();
