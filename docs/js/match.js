/* Eligibility matcher.
   Default rules follow myScheme facet tags: values inside one facet are
   alternatives, and different facets all have to fit. A field that is missing
   or "All"/"Both" is not used to exclude anyone. Amounts and age bounds come
   from the scheme record; this file does not invent them.
*/
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.YojanaMatch = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var INCOME_BANDS = {
    "under-1l": { min: 0, max: 100000 },
    "1-2.5l": { min: 100000, max: 250000 },
    "2.5-5l": { min: 250000, max: 500000 },
    "5-8l": { min: 500000, max: 800000 },
    "above-8l": { min: 800000, max: null },
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

  function explain(scheme, profile) {
    var reasons = [];
    var notes = [];
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
    var occupations = list(criteria.occupations);
    var userOccupations = OCCUPATION_LABELS[profile.occupation] || [];
    var occupationOpen = isOpen(occupations);
    var occupationHit = !occupationOpen && intersects(occupations, userOccupations);
    if (!occupationOpen && !occupationHit) reasons.push("occupation");
    // A specific occupation tag is the tighter official facet. PM-KISAN is tagged
    // Farmer and also Employed; farmers still match because the occupation fits.
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
      }
    }
    if (criteria.bplOnly === true) {
      if (profile.incomeBand !== "under-1l") reasons.push("bpl");
      else notes.push("bpl-check");
    }
    if (
      reasons.length === 0 &&
      profile.occupation === "woman_entrepreneur" &&
      profile.gender !== "Female"
    ) {
      notes.push("woman-entrepreneur-gender");
    }
    return { ok: reasons.length === 0, reasons: reasons, notes: notes };
  }

  function matches(scheme, profile) {
    return explain(scheme, profile).ok;
  }

  function matchAll(schemes, profile) {
    return schemes.filter(function (scheme) {
      return matches(scheme, profile);
    });
  }

  return {
    INCOME_BANDS: INCOME_BANDS,
    CASTE_LABELS: CASTE_LABELS,
    explain: explain,
    matches: matches,
    matchAll: matchAll,
  };
});
