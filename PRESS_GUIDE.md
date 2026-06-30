# Rescue-AI — Technical Reporter Guide
### How to Explain the Project to Press & Technical Media

---

## The One-Sentence Summary
*(Use this as your opening or when they ask "what is it in one sentence")*

> *"Rescue-AI is an open-source disaster response system that uses two AI models — one for text, one for images — to automatically triage citizen emergency reports and stream them to responders ranked by urgency, even when there's no internet."*

---

## Lead with the Real-World Problem, Not the Tech

**Don't open with:** *"We built a FastAPI backend with DistilBERT and ResNet50..."*

**Open with this:**

> *"During the 2010 Haiti earthquake, responders received 80,000 text messages in 72 hours. They had 12 people trying to read them. People died waiting to be found. We built something that reads all 80,000 in under a minute and tells you which ones are life-or-death."*

Now they're hooked. Now you explain the tech.

---

## The Narrative Arc — Tell It In This Order

### 1. The Gap
Emergency services are drowning in unstructured data during disasters. No tool exists that automatically triages citizen reports in real time. Responders either miss critical messages or waste time reading low-priority ones first.

### 2. Why AI Is the Right Answer
Rule-based systems fail. A filter for the word "fire" misses *"my house is burning"* and triggers on *"fire department doing drills."* You need a model that understands context, not keywords. That's what transformer models like DistilBERT do.

### 3. What You Actually Built
Two AI models working in parallel on every report:

- **DistilBERT** reads the citizen's text message and classifies it into 7 emergency categories — trained on real crisis tweets from the Haiti earthquake, Pakistan floods, and Nepal earthquake. It returns a category and a confidence score.

- **ResNet50** looks at the uploaded photo and identifies the type of damage — collapsed building, fire, flooding, traffic incident. It returns a severity class and confidence.

- **A priority engine** combines both scores with GPS clustering into one 0–10 urgency number, broadcast via WebSocket to every connected dashboard in real time.

### 4. The Genuinely Novel Part — Lead With This
Every reporter will have seen "AI helps first responders." Almost none have covered **"AI that works when the internet is down."** That is your differentiator. Use this:

> *"We designed for infrastructure failure from day one. When Katrina hit, the internet went down before the flooding peaked. Our system runs on a $35 Raspberry Pi over a local WiFi hotspot — no internet required. Citizens connect to it on their phones, submit reports, they queue locally, and the moment any connectivity returns, everything syncs to the central hub automatically. Same AI. Same prioritization. The infrastructure failure doesn't stop the triage."*

### 5. The Honest Limitation
Technical reporters respect honesty more than hype. Say this before they ask:

> *"This is a decision-support tool, not a replacement for responders. The AI scores help a human prioritize — a responder still reviews every report before dispatching. The AI reasoning panel shows exactly why a score was given, so responders can understand and override it. A human is always in the loop."*

---

## The Three Things to Show Them

### Show #1 — The Simulator
Run `python simulator/generate_reports.py` while the dashboard is open.

**Say:** *"I just sent 20 citizen reports to the system simultaneously — text messages describing different emergencies. Watch."*

*20 reports appear on the dashboard, ranked by priority, in real time.*

**Say:** *"The AI read all 20 messages and ranked them by urgency in under a second. The red ones at the top are people trapped or injured. The green ones at the bottom are minor road debris. No human made any of those decisions."*

---

### Show #2 — The AI Reasoning Panel
Click the top-ranked report to open the detail modal.

**Say:** *"This report scored 9.2 out of 10. Here's exactly why — it's not a black box. DistilBERT classified the text as 'people trapped' with 94% confidence. ResNet50 identified the photo as a collapsed building with 81% confidence. And there were 3 other reports submitted within 500 meters, which triggered the location clustering score. The formula is transparent: 60% text, 30% image, 10% location. A responder can read this panel in five seconds and understand the AI's reasoning — and override it if they disagree."*

---

### Show #3 — Live Submission
Go to http://localhost:3000/citizen. Type a message yourself and submit.

**Better yet — hand them the laptop and let them type it.**

**Say:** *"Type anything — describe an emergency."*

*They submit. It appears ranked on the dashboard in real time.*

**Say:** *"One second. That's the full pipeline — NLP classification, priority scoring, database write, WebSocket broadcast to every connected dashboard. That's what a real responder would see the moment a citizen hits submit."*

---

## Your Best Quotable Lines

*Select 2–3 of these. Don't use all of them — pick what feels natural.*

- *"We trained on tweets from real disasters — Haiti 2010, Pakistan floods, Nepal earthquake. The model has seen what crisis language actually looks like at scale."*

- *"The AI isn't replacing the responder. It's making sure the responder reads the right message first."*

- *"Most AI disaster tools assume you have internet. We built for the scenario where you don't — because that's exactly when it matters most."*

- *"The formula is transparent: 60% text, 30% image, 10% location. If a responder disagrees with a score, they can see exactly why it was given and override it."*

- *"A single report saying 'fire on Main St' gets a moderate score. Five reports from the same block in ten minutes gets a critical score. The clustering is how the system knows the difference between one person being dramatic and an actual neighbourhood emergency."*

- *"We froze the early layers of ResNet50 — the parts that detect edges and textures — because ImageNet already trained those perfectly. We only retrained the layers that learn high-level concepts, teaching it the difference between flood water and a clear road."*

---

## Questions They Will Definitely Ask

**"How accurate is it?"**
> "DistilBERT hits 85%+ accuracy on our test set, ResNet50 hits 88% validation accuracy. But accuracy isn't the most important metric for this problem — recall is. Missing a critical report is far worse than flagging a low-priority one too high. The hybrid approach — AI combined with keyword matching — means a word like 'trapped' or 'collapsed' always gets flagged even when the model is uncertain."

---

**"Has it been tested in a real disaster?"**
> "Not yet — this is a research prototype built for ImagineRIT. The dataset it trained on is from real disasters, and the system architecture mirrors what real emergency management systems look like. The next step would be a pilot with a local emergency management agency, which would need further validation and regulatory review before any real deployment."

---

**"What stops people from spamming fake reports?"**
> "Right now, nothing — this is a prototype. In production you'd add rate limiting by GPS location and device fingerprint, and human review above a certain priority threshold before any dispatch happens. The location clustering actually helps here — a single fake report from nowhere doesn't move the needle. It takes multiple reports from the same area to trigger the highest location risk scores."

---

**"Why not just use ChatGPT or call an API?"**
> "Three reasons: latency, cost, and offline capability. An API call to ChatGPT over the internet takes hundreds of milliseconds and requires connectivity — in a major disaster, internet is often the first thing that fails. Our models run on-device in milliseconds with no API cost and no connectivity requirement. For emergency response infrastructure, local inference isn't a nice-to-have, it's a requirement."

---

**"What's the difference between the two AI models?"**
> "DistilBERT is a language model — it reads text and understands what it means in context, the way a human would. ResNet50 is a vision model — it looks at pixels and identifies what's in the image. They're solving completely different problems using completely different techniques, but both output a score on the same 0–10 scale so the priority engine can combine them cleanly."

---

**"How did you train the image model?"**
> "We started with ResNet50 pretrained on ImageNet — 1.2 million images across 1000 categories. It already knows how to detect edges, textures, shapes. We froze those early layers and only retrained the last block and classification head on the AIDER disaster dataset — aerial and ground-level disaster photos labeled by damage type. This is called transfer learning. It let us achieve 88% accuracy with a relatively small disaster-specific dataset."

---

**"Why DistilBERT and not a larger model?"**
> "DistilBERT runs on CPU in milliseconds. Larger models like BERT-large or GPT variants are slower, heavier, and require GPU for real-time inference. For emergency response — especially Phase 2 where we're running on a Raspberry Pi with no GPU — millisecond inference on CPU is a hard requirement, not a preference. DistilBERT retains 97% of BERT's performance at 40% of the size."

---

**"What happens if the AI gets the priority wrong?"**
> "The system is designed for this. Every report shows the full AI reasoning — NLP class, confidence score, image class, location cluster — so a responder can immediately see why a score was assigned. They can dispatch a lower-ranked report if their experience tells them something is wrong. The AI is a tool that surfaces information faster; the decision authority stays with the human responder."

---

**"Could this actually be deployed by a real emergency agency?"**
> "The architecture is built for it. The backend is a standard FastAPI service, the database can swap from SQLite to PostgreSQL for production, and the mesh relay is designed to run on commodity hardware. The real barriers to deployment are regulatory — emergency management systems need certification and validation processes that take years. But technically, the path from prototype to pilot is shorter than you might think."

---

## Technical Terms — Simple Explanations for Your Audience

| Term | Say This Instead |
|------|-----------------|
| DistilBERT | A language AI trained on billions of sentences to understand what words mean in context — not just keyword matching |
| ResNet50 | An image AI that learned to identify objects from 1.2 million photos, retrained to recognize disaster damage types |
| Transfer Learning | Starting with an AI that already knows the basics — like hiring a doctor and training them to specialize, rather than starting from medical school |
| Fine-tuning | Adjusting the last layers of a pre-trained model on your specific data — only the "specialist knowledge" changes |
| WebSocket | A persistent connection between browser and server — instead of asking "any updates?" every few seconds, the server pushes new reports the instant they arrive |
| Priority Engine | The formula combining NLP score, vision score, and location clustering into one 0–10 urgency number |
| Mesh Network | Devices communicating directly over local WiFi without touching the internet |
| Transformer model | An AI architecture that reads entire sentences at once rather than word-by-word, capturing long-range context and meaning |

---

## Background Facts for Context

| Fact | Source |
|------|--------|
| Haiti earthquake — 80,000+ texts to Crisis Text Line in 72 hours | Crisis Commons, 2010 |
| Training data: CrisisNLP Crowdflower dataset — real tweets from Haiti, Pakistan floods, Nepal earthquake | CrisisNLP Research Group |
| Training data: AIDER — Aerial Image Dataset for Emergency Response | Published disaster imagery dataset |
| DistilBERT retains 97% of BERT performance at 60% size | Hugging Face, 2019 |
| ResNet50 pretrained on ImageNet — 1.2M images, 1000 classes | ImageNet Large Scale Visual Recognition Challenge |

---

## If You Only Have 60 Seconds

Say exactly this:

> *"We built an AI system for disaster response. Citizens send text messages and photos during an emergency. Two AI models — one reads the text, one analyzes the image — instantly rank every report by urgency and stream them to a live dashboard. Responders see what's critical first, automatically. The part that makes it different: it works with no internet. We designed it for infrastructure failure, because that's when disasters actually happen. A relay node on a $35 Raspberry Pi collects reports over local WiFi and syncs them when connectivity returns. Same AI, same triage, no internet required."*

---

*Built for Imagine RIT 2026 — Rochester Institute of Technology*
*GitHub: https://github.com/gsam99/Disaster-Management-System (branch: feature/ai-models)*
