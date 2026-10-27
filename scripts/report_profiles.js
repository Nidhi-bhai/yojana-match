const fs = require("fs");
const path = require("path");
const { matchAll, explain } = require("../docs/js/match.js");

const payload = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "schemes.json"), "utf8"));
const schemes = payload.schemes;
const bySlug = Object.fromEntries(schemes.map((scheme) => [scheme.slug, scheme]));

const profiles = [
  {
    id: "up-farmer",
    profile: { state: "Uttar Pradesh", age: 40, gender: "Male", incomeBand: "under-1l", occupation: "farmer", caste: "general", disability: false, residence: "Rural" },
    interest: ["pm-kisan", "pmfby", "kcc", "sui", "post-st", "pmmvy", "pmsby"],
  },
  {
    id: "bihar-sc-student",
    profile: { state: "Bihar", age: 18, gender: "Female", incomeBand: "under-1l", occupation: "student", caste: "sc", disability: false, residence: "Urban" },
    interest: ["post-st", "pm-kisan", "sui", "pmmvy", "csspremsobcsi"],
  },
  {
    id: "mh-woman-entrepreneur",
    profile: { state: "Maharashtra", age: 32, gender: "Female", incomeBand: "2.5-5l", occupation: "woman_entrepreneur", caste: "general", disability: false, residence: "Urban" },
    interest: ["sui", "pm-kisan", "pmuy", "pmuy2", "pmsby", "post-st"],
  },
  {
    id: "ka-senior-disability",
    profile: { state: "Karnataka", age: 67, gender: "Male", incomeBand: "under-1l", occupation: "unemployed", caste: "obc", disability: true, residence: "Rural" },
    interest: ["pm-kisan", "pmsby", "sui", "post-st"],
  },
  {
    id: "tg-st-farmer",
    profile: { state: "Telangana", age: 29, gender: "Female", incomeBand: "1-2.5l", occupation: "farmer", caste: "st", disability: false, residence: "Rural" },
    interest: ["pm-kisan", "pmfby", "sui", "post-st", "pmmvy"],
  },
];

function line(scheme) {
  const criteria = scheme.criteria || {};
  return [
    scheme.slug,
    scheme.level,
    (scheme.states || []).join("/"),
    "g=" + (criteria.genders || []).join("|"),
    "c=" + (criteria.castes || []).join("|"),
    "o=" + (criteria.occupations || []).join("|"),
    "e=" + (criteria.employment || []).join("|"),
    "r=" + (criteria.residences || []).join("|"),
    "d=" + criteria.disability,
    "st=" + criteria.studentOnly,
    "age=" + criteria.ageMin + "-" + criteria.ageMax,
    "inc=" + criteria.incomeCeilingInr,
    criteria.genderCasteMode || "",
  ].join(" ");
}

console.log("count", schemes.length);
for (const slug of ["pm-kisan", "sui", "post-st", "pmsby", "pmmvy", "pmfby", "kcc", "pmuy"]) {
  const scheme = bySlug[slug];
  console.log(scheme ? line(scheme) : "MISSING " + slug);
}
for (const item of profiles) {
  const matched = matchAll(schemes, item.profile);
  console.log("\n==", item.id, matched.length);
  for (const slug of item.interest) {
    const scheme = bySlug[slug];
    if (!scheme) {
      console.log("  missing", slug);
      continue;
    }
    const result = explain(scheme, item.profile);
    console.log(" ", slug, result.ok ? "YES" : "NO", result.reasons.join(","), result.notes.join(","));
  }
  const stateNames = matched.filter((scheme) => scheme.level === "State").slice(0, 8).map((scheme) => scheme.slug);
  console.log("  state sample", stateNames.join(", "));
}
