# Dear Tar,

Hey Tar! Super excited to finally send over your full-time position test. We've cooked up something pretty cool and can't wait to see what you will build. Knowing it's you, it's gonna be awesome! 🚀

Please note: You have a total of **7 days** to complete the test (**submit before 23:59, 8 July 2025**).

---

## 🔎 Problem – Edge AI Platform for Building Energy & IAQ Optimization

Imagine you are an AI engineer tasked with building a **production-ready Edge AI platform** that:

- Deploys **LLMs on-premise**
- Analyzes real-time IoT data from building systems (IAQ sensors and power meters)
- Provides intelligent recommendations
- Autonomously optimizes building operations

---

## 📌 Sub-Problem 1 – LLM Model Selection & Edge Deployment

### Tasks:

- Research and select the most suitable **open-source LLM** for edge deployment in a building automation context.

### Include Analysis on:

- **Model Comparison** (e.g., NVIDIA Nemotron, Llama 3.1, Mistral, Phi-3, Qwen):
  - Model size vs performance trade-offs for edge deployment
  - Quantization support (INT8/INT4) for TensorRT optimization
  - Tool/function calling capabilities
  - Context window size for time-series IoT data
  - License compatibility for commercial deployment

- **Deployment**:
  - Deploy your chosen model with **TensorRT optimization**
  - Document:
    - Resource requirements (GPU memory, compute)
    - Inference latency benchmarks
    - Throughput metrics
    - Deployment architecture decisions

➡️ Defend your model choice with clear reasoning on why it's optimal for edge AI in building automation.

---

## 📌 Sub-Problem 2 – Volttron Integration & Data Simulation

### Tasks:

- Create a realistic building automation environment.

#### Mock Data Generation:
- Write **Volttron agents** to simulate:
  - **10 IAQ sensors** publishing CO₂, temperature, and humidity every 30 seconds
  - **5 power meters** publishing real-time consumption data every 15 seconds
- Store all data in **TimescaleDB** with proper **BRICK schema** annotations

#### LLM-Volttron Bridge:
- Your LLM service should:
  - Access real-time data streams
  - Be provided with historical data via function calling
  - Offer recommendations based on IoT data

#### Real Use Cases (implement at least 3):
1. Proactive IAQ optimization recommendations
2. Energy waste detection and automatic suggestions (e.g., predicted energy over today's target)
3. Any other practical use cases using IAQ and power meter data

---

## 📌 Sub-Problem 3 – Model Evaluation & Safety

### Tasks:

Use the **NVIDIA NeMo Eval framework** to rigorously evaluate your deployment.

#### Compare:
- **Baseline vs Fine-tuned model**:
  - Tool-calling accuracy (critical for IoT control)
  - Relevance of responses for building operators
  - Latency impact
  - Any other appropriate metrics

#### Safety & Security:
- Implement **NEMO Guardrails** to:
  - Prevent harmful control command suggestions
  - Ensure safety within operational bounds
  - Handle adversarial prompts that may cause unsafe behavior

---

## 📌 Sub-Problem 4 – Production Monitoring & Observability

### Tasks:

Design a **comprehensive monitoring framework** using **LangSmith**.

#### Track:
- Usage analytics (which features operators use most)
- Recommendation acceptance rates
- Model drift over time
- Real-time latency
- Token usage and cost
- Error rates and automatic alerts
- Any other important observability metrics

---

## 📌 Sub-Problem 5 – Innovation Bonus (Optional)

Try any of the following (or more!):

- **Multi-building orchestration**: Show how your solution scales
- **Human-in-the-loop**: Let operator feedback improve the model
- Anything else creative, even beyond the scope! 🎉

---

## 🤔 What You Need to Submit

- A link to your **YouTube demo video**
- Your **GitHub repo** containing all code and discussions:
  - You may place non-code discussions in the `README.md` file
- A **sequence diagram**, **flow chart**, or **other planning diagrams**

---

## 💡 Useful Tips

- **Show Your Thinking**: Document thoughts, decisions, trade-offs, and scaling ideas
- **Focus on Value**: Demonstrate real usefulness and user impact
- We made this test challenging because we know you can handle it and want you to shine! 💪

Use any AI tools you need, and don’t hesitate to ping me if you need help. To get you started quickly, we've included some initial code in the email attachment (includes a Volttron Docker setup and a basic TimescaleDB agent).

