// File: assertions/tool_accuracy.js
function getToolsFromState(messages) {
    if (!messages || !Array.isArray(messages)) return [];
    
    let toolCalls = [];
    messages.forEach(msg => {
        if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
            msg.tool_calls.forEach(tc => {
                if(tc.name) toolCalls.push(tc.name);
            });
        }
    });
    return toolCalls;
}

// Export the main evaluation function that Promptfoo will call
module.exports = function(output, context) {
    // Fix: Ensure expected_tools is treated as an array, not split into characters
    const expectedToolsRaw = context.vars.expected_tools || [];
    const expectedTools = new Set(Array.isArray(expectedToolsRaw) ? expectedToolsRaw : []);
    
    // The full conversation history is in `meta.messages`
    const actualToolsRaw = getToolsFromState(context.vars.meta?.messages);
    const actualTools = new Set(actualToolsRaw);

    if (expectedTools.size === 0 && actualTools.size === 0) {
        // Return proper GradingResult format for Promptfoo
        return {
            pass: true,
            score: 1.0,
            reason: "Correctly called no tools."
        };
    }

    const intersection = new Set([...expectedTools].filter(x => actualTools.has(x)));
    
    const precision = actualTools.size > 0 ? intersection.size / actualTools.size : 1.0;
    const recall = expectedTools.size > 0 ? intersection.size / expectedTools.size : 1.0;
    
    let f1 = 0;
    if (precision + recall > 0) {
        f1 = 2 * (precision * recall) / (precision + recall);
    }

    const reason = `Precision: ${precision.toFixed(2)}, Recall: ${recall.toFixed(2)}, F1: ${f1.toFixed(2)}. Expected: [${[...expectedTools].join(', ')}], Actual: [${[...actualTools].join(', ')}]`;

    // Return proper GradingResult format that Promptfoo expects
    return {
        pass: f1 >= 0.75,
        score: f1,
        reason: reason
    };
};