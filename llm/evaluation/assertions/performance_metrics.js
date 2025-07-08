// File: assertions/performance_metrics.js
function evaluatePerformanceMetrics(output, context) {
    // Metadata comes from the 'meta' field in the provider's return value
    const metadata = context.vars.meta || {};
    const query = context.vars.query || '';
    let scores = {};

    // LATENCY PERFORMANCE
    const latency = metadata.latency_ms || 0;
    if (latency > 0) {
        if (latency <= 8000) scores.latencyScore = 1.0;
        else if (latency <= 15000) scores.latencyScore = 0.7;
        else scores.latencyScore = 0.2;
    } else {
        scores.latencyScore = 0.5; // Unknown latency
    }

    // CONFIDENCE CALIBRATION
    const confidence = metadata.confidence_score || 0;
    scores.confidenceScore = confidence > 0.75 ? 1.0 : confidence / 0.75;
    
    // ERROR HANDLING
    const hasError = metadata.status === 'error' || output.includes('Error:');
    scores.errorScore = hasError ? 0.0 : 1.0;

    // AGGREGATE PERFORMANCE SCORE
    const performanceScore = (
        scores.latencyScore * 0.5 +       // 50% weight on speed
        scores.confidenceScore * 0.3 +    // 30% weight on confidence
        scores.errorScore * 0.2           // 20% weight on error-free operation
    );

    return {
        pass: performanceScore > 0.7,
        score: performanceScore,
        message: `Latency: ${latency.toFixed(0)}ms, Confidence: ${confidence.toFixed(2)}`
    };
}

return evaluatePerformanceMetrics(output, context); 