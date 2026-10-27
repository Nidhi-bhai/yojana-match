/* Eligibility matcher.
   Facets still come from myScheme. A missing or "All"/"Both" facet does not,
   by itself, make a scheme a match. A scheme is a match only when every
   structured rule fits. Extra conditions that are quoted but not asked as a
   question, and schemes with no real restriction, are "possible" (check the
   conditions) and are never returned as matches. Closed schemes are neither.
*/
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.YojanaMatch = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var AS_OF = "2026-10-27";
  var INCOME_BANDS = {
    "under-1l": { min: 0, max: 100000 },
    "1-2.5l": { min: 100000, max: 250000 },
    "2.5-5l": { min: 250000, max: 500000 },
    "5-8l": { min: 500000, max: 800000 },
    // "Above ₹8,00,000" starts past the 8 lakh line.
    "above-8l": { min: 800001, max: null },
  };

  var CASTE_LABELS = {
    general: ["General"],
    obc: ["Other Backward Class (OBC)"],
    sc: ["Scheduled Caste (SC)"],
    st: ["Scheduled Tribe (ST)"],
    pvtg: [
      "Particularly Vulnerable Tribal Group (PVTG)",
      "Scheduled Tribe (ST)",
    ],
    dnt: ["De-Notified, Nomadic, and Semi-Nomadic (DNT) communities"],
  };

  var OCCUPATION_LABELS = {
    farmer: ["Farmer"],
    student: ["Student"],
    msme: [],
    woman_entrepreneur: [],
    salaried: ["Organized Worker"],
    unemployed: [],
    other: [],
  };

  var EMPLOYMENT_LABELS = {
    farmer: ["Self-Employed/ Entrepreneur"],
    student: [],
    msme: ["Self-Employed/ Entrepreneur"],
    woman_entrepreneur: ["Self-Employed/ Entrepreneur"],
    salaried: ["Employed"],
    unemployed: ["Unemployed"],
    other: [],
  };

  var SC_ST = ["Scheduled Caste (SC)", "Scheduled Tribe (ST)"];

  function list(value) {
    return Array.isArray(value) ? value : [];
  }

  function isOpen(values, openValues) {
    if (!values || values.length === 0) return true;
    var opens = openValues || ["All"];
    for (var i = 0; i < values.length; i += 1) {
      if (opens.indexOf(values[i]) !== -1) return true;
    }
    return false;
  }

  function intersects(values, wanted) {
    if (!wanted || !wanted.length) return false;
    for (var i = 0; i < wanted.length; i += 1) {
      if (values.indexOf(wanted[i]) !== -1) return true;
    }
    return false;
  }

  function pushUnique(reasons, code) {
    if (reasons.indexOf(code) === -1) reasons.push(code);
  }

  function isClosed(scheme) {
    return Boolean(scheme && scheme.closeDate && scheme.closeDate < AS_OF);
  }

  function genderCasteFails(scheme, profile) {
    var criteria = scheme.criteria || {};
    var castes = CASTE_LABELS[profile.caste] || [];
    if (criteria.genderCasteMode === "male-must-be-sc-st") {
      if (profile.gender === "Female") return false;
      if (profile.gender === "Male") return !intersects(SC_ST, castes);
      return true;
    }
    var genders = list(criteria.genders);
    if (!isOpen(genders) && genders.indexOf(profile.gender) === -1) return true;
    var schemeCastes = list(criteria.castes);
    if (!isOpen(schemeCastes) && !intersects(schemeCastes, castes)) return true;
    return false;
  }

  function residenceFails(criteria, profile) {
    var residences = list(criteria.residences);
    if (isOpen(residences, ["Both", "All"])) return false;
    if (residences.indexOf("Rural") !== -1 && residences.indexOf("Urban") !== -1) {
      return false;
    }
    return residences.indexOf(profile.residence) === -1;
  }

  function specialGroupFails(criteria, profile) {
    var needed = list(criteria.specialGroups);
    if (!needed.length) return false;
    var selected = list(profile.groups);
    if ((criteria.specialGroupMode || "any") === "all") {
      for (var i = 0; i < needed.length; i += 1) {
        if (selected.indexOf(needed[i]) === -1) return true;
      }
      return false;
    }
    return !intersects(needed, selected);
  }

  function ageRestricts(criteria) {
    var ageMin = criteria.ageMin;
    var ageMax = criteria.ageMax;
    if (typeof ageMin === "number" && ageMin >= 40) return true;
    if (typeof ageMax === "number" && ageMax <= 35) return true;
    if (typeof ageMin === "number" && typeof ageMax === "number" && ageMax - ageMin <= 30) {
      return true;
    }
    return false;
  }

  function isBroad(scheme) {
    var criteria = scheme.criteria || {};
    if (criteria.studentOnly === true) return false;
    if (criteria.bplOnly === true || criteria.listingRequired === true) return false;
    if (criteria.disability === "Yes") return false;
    if (list(criteria.specialGroups).length) return false;
    if (typeof criteria.incomeCeilingInr === "number") return false;
    var states = list(scheme.states);
    if (states.length && states.indexOf("All") === -1) return false;
    if (!isOpen(list(criteria.genders))) return false;
    if (!isOpen(list(criteria.castes))) return false;
    var residences = list(criteria.residences);
    if (!isOpen(residences, ["Both", "All"])) {
      if (!(residences.indexOf("Rural") !== -1 && residences.indexOf("Urban") !== -1)) {
        return false;
      }
    }
    if (!isOpen(list(criteria.occupations))) return false;
    if (!isOpen(list(criteria.employment))) return false;
    if (ageRestricts(criteria)) return false;
    return true;
  }

  function explain(scheme, profile) {
    var reasons = [];
    var notes = [];
    var checks = [];
    if (isClosed(scheme)) {
      return { ok: false, status: "closed", reasons: ["closed"], notes: notes, checks: checks };
    }
    var criteria = scheme.criteria || {};
    var states = list(scheme.states);
    if (
      states.length &&
      states.indexOf("All") === -1 &&
      states.indexOf(profile.state) === -1
    ) {
      reasons.push("state");
    }
    if (genderCasteFails(scheme, profile)) reasons.push("gender-or-caste");
    if (residenceFails(criteria, profile)) reasons.push("residence");
    if (criteria.disability === "Yes" && !profile.disability) reasons.push("disability");
    if (criteria.studentOnly === true && profile.occupation !== "student") {
      reasons.push("student");
    }
    if (specialGroupFails(criteria, profile)) reasons.push("special-group");
    var occupations = list(criteria.occupations);
    var userOccupations = OCCUPATION_LABELS[profile.occupation] || [];
    var occupationOpen = isOpen(occupations);
    var occupationHit = !occupationOpen && intersects(occupations, userOccupations);
    if (!occupationOpen && !occupationHit) reasons.push("occupation");
    var employment = list(criteria.employment);
    var userEmployment = EMPLOYMENT_LABELS[profile.occupation] || [];
    if (!occupationHit && !isOpen(employment) && !intersects(employment, userEmployment)) {
      reasons.push("employment");
    }
    if (typeof criteria.ageMin === "number" && profile.age < criteria.ageMin) {
      pushUnique(reasons, "age");
    }
    if (typeof criteria.ageMax === "number" && profile.age > criteria.ageMax) {
      pushUnique(reasons, "age");
    }
    var band = INCOME_BANDS[profile.incomeBand];
    if (band && typeof criteria.incomeCeilingInr === "number") {
      if (band.min > criteria.incomeCeilingInr) {
        reasons.push("income");
      } else if (band.max == null || band.max > criteria.incomeCeilingInr) {
        notes.push("income-check");
        checks.push({ code: "income-check", quote: criteria.incomeCeilingNote || "" });
      }
    }
    var listingRequired = criteria.listingRequired === true || criteria.bplOnly === true;
    var listing = profile.listing || "not-sure";
    if (listingRequired) {
      if (listing === "no") {
        reasons.push("listing");
      } else if (listing === "not-sure" || criteria.listingDetail === true) {
        // "Not sure", and a yes that still leaves SECC or ration-card wording, stay in the check section.
        checks.push({
          code: listing === "not-sure" ? "listing" : "listing-detail",
          quote: criteria.listingQuote || "",
        });
      }
    }
    list(criteria.uncertain).forEach(function (item) {
      checks.push({ code: item.code || "condition", quote: item.quote || "" });
    });
    if (
      reasons.length === 0 &&
      profile.occupation === "woman_entrepreneur" &&
      profile.gender !== "Female"
    ) {
      notes.push("woman-entrepreneur-gender");
    }
    if (reasons.length === 0 && isBroad(scheme)) {
      checks.push({ code: "broad", quote: "" });
    }
    var status = "match";
    if (reasons.length) status = "no";
    else if (checks.length) status = "possible";
    return { ok: status === "match", status: status, reasons: reasons, notes: notes, checks: checks };
  }

  function matches(scheme, profile) {
    return explain(scheme, profile).status === "match";
  }

  function matchAll(schemes, profile) {
    return schemes.filter(function (scheme) {
      return matches(scheme, profile);
    });
  }

  function possibleAll(schemes, profile) {
    return schemes.filter(function (scheme) {
      return explain(scheme, profile).status === "possible";
    });
  }

  return {
    AS_OF: AS_OF,
    INCOME_BANDS: INCOME_BANDS,
    CASTE_LABELS: CASTE_LABELS,
    explain: explain,
    matches: matches,
    matchAll: matchAll,
    possibleAll: possibleAll,
    isClosed: isClosed,
    isBroad: isBroad,
  };
});
