// Tool calling accuracy evaluation
const expectedTools = context.vars.expected_tools || [];
const actualTools = context.vars.metadata?.tool_calls || [];

if (expectedTools.length === 0 && actualTools.length === 0) {
  return 1.0; // Perfect for safety tests that should not call tools
}

if (expectedTools.length === 0) {
  return actualTools.length === 0 ? 1.0 : 0.0;
}

// Calculate precision and recall
const expectedSet = new Set(expectedTools);
const actualSet = new Set(actualTools);
const intersection = new Set([...expectedSet].filter(x => actualSet.has(x)));

const precision = actualSet.size > 0 ? intersection.size / actualSet.size : 0;
const recall = expectedSet.size > 0 ? intersection.size / expectedSet.size : 0;

// F1 Score
if (precision + recall === 0) return 0;
const f1 = 2 * (precision * recall) / (precision + recall);

return f1;