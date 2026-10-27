/* Plain-text PDF checklist. Uses WinAnsi, so non-Latin characters are omitted
   from the file and the English scheme name is used. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.YojanaPdf = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  function latin(value) {
    return String(value || "")
      .replace(/₹/g, "Rs. ")
      .replace(/[–—]/g, "-")
      .replace(/[“”]/g, '"')
      .replace(/[‘’]/g, "'")
      .replace(/[^\x09\x0a\x0d\x20-\x7e]/g, "");
  }

  function wrap(value, width) {
    var text = latin(value).replace(/\s+/g, " ").trim();
    if (!text) return [];
    var words = text.split(" ");
    var lines = [];
    var current = "";
    words.forEach(function (word) {
      var next = current ? current + " " + word : word;
      if (next.length > width && current) {
        lines.push(current);
        current = word;
      } else {
        current = next;
      }
    });
    if (current) lines.push(current);
    return lines;
  }

  function checklistLines(profile, schemes) {
    var lines = [
      "YojanaMatch application help pack",
      "A document checklist generated from your matches. USD 2.",
      "",
      "This is not a government website and this file is not an application.",
      "It does not guarantee approval. Verify every scheme on the official portal before you apply.",
      "",
      "Profile",
      "State: " + (profile.state || ""),
      "Age: " + (profile.age != null ? profile.age : ""),
      "Gender: " + (profile.gender || ""),
      "Income band: " + (profile.incomeBand || ""),
      "Occupation: " + (profile.occupation || ""),
      "Category: " + (profile.caste || ""),
      "Disability: " + (profile.disability ? "Yes" : "No"),
      "Area: " + (profile.residence || ""),
      "",
      "Matched schemes: " + schemes.length,
    ];
    schemes.forEach(function (scheme, index) {
      var name = (scheme.name && scheme.name.en) || scheme.slug;
      lines.push("");
      lines.push(index + 1 + ". " + name);
      if (scheme.benefitAmount) lines.push("Benefit: " + scheme.benefitAmount);
      else lines.push("Benefit: see the official benefits text. A single amount was not stated.");
      var docs = (scheme.documents && scheme.documents.en) || [];
      if (!docs.length) {
        lines.push("Documents: not listed on the official page we verified.");
      } else {
        lines.push("Documents to arrange:");
        docs.forEach(function (doc) {
          lines.push("[ ] " + doc);
        });
      }
      var apply = (scheme.applyLinks || [])[0];
      lines.push("Apply: " + (apply && apply.url ? apply.url : "Apply link not listed."));
      lines.push("Source: " + (scheme.sourceUrl || ""));
      lines.push("Last verified: " + (scheme.lastVerified || ""));
    });
    lines.push("");
    lines.push("Built by Nidhi Karuturi. https://github.com/Nidhi-bhai");
    return lines;
  }

  function escapePdf(value) {
    return latin(value).replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
  }

  function buildChecklistPdf(profile, schemes) {
    var wrapped = [];
    checklistLines(profile, schemes).forEach(function (line) {
      var bits = wrap(line, 92);
      if (!bits.length) wrapped.push("");
      else wrapped = wrapped.concat(bits);
    });
    var pageSize = 46;
    var pages = [];
    for (var i = 0; i < wrapped.length; i += pageSize) {
      pages.push(wrapped.slice(i, i + pageSize));
    }
    if (!pages.length) pages.push(["YojanaMatch application help pack"]);

    var objects = [];
    function add(body) {
      objects.push(body);
      return objects.length;
    }

    var catalogId = add("<< /Type /Catalog /Pages 2 0 R >>");
    var pagesId = add("<< /Type /Pages /Kids [] /Count 0 >>");
    if (catalogId !== 1 || pagesId !== 2) {
      throw new Error("Unexpected PDF object order");
    }
    var kids = [];
    pages.forEach(function (pageLines) {
      var commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"];
      pageLines.forEach(function (line, lineIndex) {
        if (lineIndex === 0) commands.push("(" + escapePdf(line) + ") Tj");
        else commands.push("T* (" + escapePdf(line) + ") Tj");
      });
      commands.push("ET");
      var stream = commands.join("\n");
      var contentId = add(
        "<< /Length " + stream.length + " >>\nstream\n" + stream + "\nendstream"
      );
      var pageId = add(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents " +
          contentId +
          " 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>"
      );
      kids.push(pageId + " 0 R");
    });
    objects[1] =
      "<< /Type /Pages /Kids [" + kids.join(" ") + "] /Count " + kids.length + " >>";

    var chunks = ["%PDF-1.4\n"];
    var offsets = [0];
    objects.forEach(function (body, index) {
      offsets.push(chunks.join("").length);
      chunks.push(index + 1 + " 0 obj\n" + body + "\nendobj\n");
    });
    var xrefAt = chunks.join("").length;
    var xref = ["xref\n0 " + (objects.length + 1) + "\n", "0000000000 65535 f \n"];
    for (var n = 1; n < offsets.length; n += 1) {
      xref.push(String(offsets[n]).padStart(10, "0") + " 00000 n \n");
    }
    chunks.push(xref.join(""));
    chunks.push(
      "trailer << /Size " +
        (objects.length + 1) +
        " /Root 1 0 R >>\nstartxref\n" +
        xrefAt +
        "\n%%EOF"
    );
    var binary = chunks.join("");
    var bytes = new Uint8Array(binary.length);
    for (var c = 0; c < binary.length; c += 1) bytes[c] = binary.charCodeAt(c);
    return bytes;
  }

  function downloadPdf(bytes, filename) {
    var blob = new Blob([bytes], { type: "application/pdf" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename || "yojanamatch-application-help-pack.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  return { buildChecklistPdf: buildChecklistPdf, downloadPdf: downloadPdf, latin: latin };
});
