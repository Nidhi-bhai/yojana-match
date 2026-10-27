const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const { explain, matchAll } = require("../docs/js/match.js");
const { buildChecklistPdf } = require("../docs/js/pdf.js");

function scheme(overrides) {
  return Object.assign(
    {
      slug: "sample",
      name: { en: "Sample Scheme" },
      states: ["All"],
      level: "Central",
      benefitAmount: "",
      documents: { en: ["Aadhaar"] },
      applyLinks: [{ mode: "Online", url: "https://example.gov.in/apply" }],
      sourceUrl: "https://www.myscheme.gov.in/schemes/sample",
      lastVerified: "2026-10-27",
      criteria: {
        genders: ["All"],
        castes: ["All"],
        residences: ["Both"],
        occupations: ["All"],
        employment: ["All"],
        disability: "No",
        studentOnly: false,
        bplOnly: false,
        ageMin: null,
        ageMax: null,
        incomeCeilingInr: null,
      },
    },
    overrides
  );
}

const farmer = {
  state: "Uttar Pradesh",
  age: 40,
  gender: "Male",
  incomeBand: "under-1l",
  occupation: "farmer",
  caste: "general",
  disability: false,
  residence: "Rural",
};

test("open central scheme matches a farmer", () => {
  assert.equal(explain(scheme(), farmer).ok, true);
});

test("another state's scheme is excluded", () => {
  const row = scheme({ states: ["Tamil Nadu"], level: "State" });
  assert.deepEqual(explain(row, farmer).reasons, ["state"]);
});

test("women-only scheme excludes a man", () => {
  const row = scheme({ criteria: { genders: ["Female"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false } });
  assert.equal(explain(row, farmer).ok, false);
});

test("SC scheme matches an SC woman and a PVTG beneficiary matches an ST scheme", () => {
  const sc = scheme({ criteria: { genders: ["All"], castes: ["Scheduled Caste (SC)"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false } });
  assert.equal(explain(sc, Object.assign({}, farmer, { caste: "sc", gender: "Female" })).ok, true);
  assert.equal(explain(sc, farmer).ok, false);
  const st = scheme({ criteria: { genders: ["All"], castes: ["Scheduled Tribe (ST)"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false } });
  assert.equal(explain(st, Object.assign({}, farmer, { caste: "pvtg" })).ok, true);
});

test("rural, disability, student, and occupation gates", () => {
  const rural = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Rural"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false } });
  assert.equal(explain(rural, Object.assign({}, farmer, { residence: "Urban" })).ok, false);
  const pwd = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "Yes", studentOnly: false, bplOnly: false } });
  assert.equal(explain(pwd, farmer).ok, false);
  assert.equal(explain(pwd, Object.assign({}, farmer, { disability: true })).ok, true);
  const student = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["Student"], employment: ["All"], disability: "No", studentOnly: true, bplOnly: false } });
  assert.equal(explain(student, farmer).ok, false);
  assert.equal(explain(student, Object.assign({}, farmer, { occupation: "student", age: 18 })).ok, true);
});

test("age and income use only stated bounds", () => {
  const pension = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false, ageMin: 60, ageMax: null } });
  assert.equal(explain(pension, farmer).ok, false);
  assert.equal(explain(pension, Object.assign({}, farmer, { age: 65 })).ok, true);
  const capped = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: false, incomeCeilingInr: 250000 } });
  assert.equal(explain(capped, Object.assign({}, farmer, { incomeBand: "above-8l" })).ok, false);
  const inside = explain(capped, Object.assign({}, farmer, { incomeBand: "under-1l" }));
  assert.equal(inside.ok, true);
  assert.equal(inside.notes.includes("income-check"), false);
  const straddle = explain(capped, Object.assign({}, farmer, { incomeBand: "2.5-5l" }));
  assert.equal(straddle.ok, true);
  assert.ok(straddle.notes.includes("income-check"));
});

test("male SC/ST rule follows the official sentence", () => {
  const row = scheme({
    criteria: {
      genders: ["Female", "Male"],
      castes: ["Scheduled Caste (SC)", "Scheduled Tribe (ST)"],
      residences: ["Both"],
      occupations: ["All"],
      employment: ["All"],
      disability: "No",
      studentOnly: false,
      bplOnly: false,
      ageMin: 18,
      genderCasteMode: "male-must-be-sc-st",
      genderCasteQuote: "If the applicant is a male, he must be from SC / ST category.",
    },
  });
  const woman = Object.assign({}, farmer, { gender: "Female", occupation: "woman_entrepreneur", residence: "Urban", incomeBand: "2.5-5l", age: 32 });
  assert.equal(explain(row, woman).ok, true);
  assert.equal(explain(row, farmer).ok, false);
  assert.equal(explain(row, Object.assign({}, farmer, { caste: "sc" })).ok, true);
  assert.equal(explain(row, Object.assign({}, woman, { gender: "Transgender" })).ok, false);
});

test("bpl schemes stay with the lowest income band", () => {
  const row = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["All"], disability: "No", studentOnly: false, bplOnly: true } });
  assert.equal(explain(row, farmer).ok, true);
  assert.equal(explain(row, Object.assign({}, farmer, { incomeBand: "2.5-5l" })).ok, false);
});

test("a farmer scheme tagged Employed still matches farmers", () => {
  const row = scheme({
    criteria: {
      genders: ["All"],
      castes: ["All"],
      residences: ["Both"],
      occupations: ["Farmer"],
      employment: ["Employed"],
      disability: "No",
      studentOnly: false,
      bplOnly: false,
      ageMin: 18,
    },
  });
  assert.equal(explain(row, farmer).ok, true);
  assert.equal(explain(row, Object.assign({}, farmer, { occupation: "student", age: 18 })).ok, false);
});

test("employment separates salaried work from self-employment", () => {
  const row = scheme({ criteria: { genders: ["All"], castes: ["All"], residences: ["Both"], occupations: ["All"], employment: ["Self-Employed/ Entrepreneur"], disability: "No", studentOnly: false, bplOnly: false } });
  assert.equal(explain(row, Object.assign({}, farmer, { occupation: "msme" })).ok, true);
  assert.equal(explain(row, Object.assign({}, farmer, { occupation: "salaried" })).ok, false);
});

test("checklist pdf is a real pdf and does not invent a benefit", () => {
  const bytes = buildChecklistPdf(farmer, [scheme({ benefitAmount: "" })]);
  const text = Buffer.from(bytes).toString("latin1");
  assert.ok(text.startsWith("%PDF-1.4"));
  assert.ok(text.includes("Sample Scheme"));
  assert.ok(text.includes("not a government website"));
  assert.ok(text.includes("A single amount was not stated"));
  assert.ok(text.includes("%%EOF"));
});

test("database profiles are consistent when the catalog is present", () => {
  const fs = require("fs");
  const file = path.join(__dirname, "..", "data", "schemes.json");
  if (!fs.existsSync(file)) {
    return;
  }
  const payload = JSON.parse(fs.readFileSync(file, "utf8"));
  assert.ok(payload.schemes.length >= 150);
  const slugs = new Set();
  for (const row of payload.schemes) {
    assert.equal(row.sourceUrl, `https://www.myscheme.gov.in/schemes/${row.slug}`);
    assert.equal(row.lastVerified, "2026-10-27");
    assert.ok(row.name.en);
    assert.ok(!slugs.has(row.slug));
    slugs.add(row.slug);
    assert.equal(typeof row.benefitAmount, "string");
    if (row.benefitAmount) assert.match(row.benefitAmount, /\d/);
    for (const link of row.applyLinks || []) {
      assert.match(link.url, /^https?:\/\//);
    }
  }
  const profiles = require("./profiles.json");
  for (const item of profiles) {
    const matched = new Set(matchAll(payload.schemes, item.profile).map((row) => row.slug));
    for (const slug of item.mustInclude) {
      assert.ok(matched.has(slug), `${item.id} should include ${slug}`);
    }
    for (const slug of item.mustExclude) {
      assert.equal(matched.has(slug), false, `${item.id} should exclude ${slug}`);
    }
  }
});
