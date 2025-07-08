// Building automation domain knowledge evaluation
const output = output.toLowerCase();

// Core building automation terms
const basicTerms = ['zone', 'building', 'hvac', 'temperature', 'system'];
const intermediateTerms = ['co2', 'ppm', 'ventilation', 'energy', 'power', 'consumption'];
const advancedTerms = ['iaq', 'cross-zone', 'optimization', 'chiller', 'damper', 'setpoint'];

// Score calculation
let score = 0;
const totalPossible = basicTerms.length * 0.3 + intermediateTerms.length * 0.5 + advancedTerms.length * 0.7;

// Count terms in each category
basicTerms.forEach(term => {
  if (output.includes(term)) score += 0.3;
});

intermediateTerms.forEach(term => {
  if (output.includes(term)) score += 0.5;
});

advancedTerms.forEach(term => {
  if (output.includes(term)) score += 0.7;
});

// Bonus for specific zone references
const zoneReferences = (output.match(/zone[_\s]*\d+[_\s]*\d+/g) || []).length;
if (zoneReferences > 0) score += 0.2;

// Normalize to 0-1 scale
return Math.min(1.0, score / totalPossible);