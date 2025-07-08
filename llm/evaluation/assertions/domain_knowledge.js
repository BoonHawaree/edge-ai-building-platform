// File: assertions/domain_knowledge.js
function assessDomainKnowledge(output, context) {
    const output_lower = (output || '').toLowerCase();
    let score = 0;
    let findings = [];

    // Key building automation terms
    const terms = {
        basic: ['zone', 'building', 'hvac', 'temperature', 'system'],
        intermediate: ['co2', 'ppm', 'ventilation', 'energy', 'power', 'consumption'],
        advanced: ['iaq', 'cross-zone', 'optimization', 'chiller', 'damper', 'setpoint']
    };

    let totalPossible = 0;
    let termsFound = 0;

    // Score based on term usage
    for (const term of terms.basic) { totalPossible += 0.5; if (output_lower.includes(term)) { score += 0.5; termsFound++; } }
    for (const term of terms.intermediate) { totalPossible += 1.0; if (output_lower.includes(term)) { score += 1.0; termsFound++; } }
    for (const term of terms.advanced) { totalPossible += 1.5; if (output_lower.includes(term)) { score += 1.5; termsFound++; } }
    
    // Bonus for specific zone references (e.g., "zone 1_1", "zone 2_3")
    if (/zone.*\d+[_\s]*\d+/i.test(output)) {
        score += 2.0;
        totalPossible += 2.0;
        findings.push("Identified specific zone.");
    }

    // Bonus for mentioning zone names from the system prompt
    const zoneNames = ['lobby', 'conference room', 'restaurant', 'co-working', 'office'];
    for(const name of zoneNames) {
      if(output_lower.includes(name)) {
        score += 1.0;
        totalPossible += 1.0;
        findings.push(`Mentioned zone name: ${name}`);
        break; // one is enough
      }
    }

    const normalizedScore = totalPossible > 0 ? score / totalPossible : 0;
    
    return {
        pass: normalizedScore > 0.6,
        score: normalizedScore,
        message: `Found ${termsFound} domain terms. ${findings.join(' ')}`
    };
}

return assessDomainKnowledge(output, context); 