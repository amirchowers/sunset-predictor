# Future Vision

Where Sunset Predictor goes from a local macOS tool to a product people pay attention to.

---

## 1. Instagram Auto-Posting

**What:** Daily post at sunset with the best webcam frame, overlaid score, and a one-line verdict.

**Why it matters:** Sunsets are the most-shared natural phenomenon on Instagram. A bot that posts a scored sunset photo every day from the same location builds a visual archive and an audience — no manual effort required.

**How it works:**
- At sunset+20min, pick the highest-AI-rated frame from the capture window
- Overlay the score and verdict (e.g. "8.2 — Tell your friends") using Pillow
- Post via Instagram Graph API with location tag and hashtags
- Track engagement (likes, saves) as a signal of whether the score resonated

**Revenue angle:** None directly — this is an audience-building channel that feeds the push notification app below.

---

## 2. Push Notification App (Sunset Alerts)

**What:** A lightweight mobile app (or PWA) that sends a push notification 2-3 hours before any sunset scoring 7+.

**Why it matters:** The core insight — "Is tonight worth going outside for?" — is more valuable as a push notification than a Telegram message. A dedicated app lets you reach people who don't use Telegram and opens a monetization path.

**How it works:**
- Backend: the existing scoring engine exposed as an API endpoint
- Push delivery: Firebase Cloud Messaging (free tier covers tens of thousands of users)
- User sets their threshold (default: 7+) and preferred notification time
- Optional: "Sunset now!" real-time alert when the capture confirms the prediction was right

**Revenue angle:** Hyper-local ads from rooftop bars, beach restaurants, and sunset cruise operators. A notification that says "Tonight's sunset: 8.5 — watch it from Skyline Rooftop Bar (200m away)" is genuinely useful, not spammy. CPM on location-based sunset alerts to an engaged audience could be $15-30.

---

## 3. Multi-City Expansion

**What:** Same scoring model, any coastal city. API: `GET /predict?lat=32.08&lon=34.78`

**Why it matters:** The scoring engine is location-agnostic — it already uses Open-Meteo (global coverage) and computes western sky geometry from lat/lon. The only city-specific piece is the webcam registry, and that's a simple config addition per city.

**Expansion path:**
1. **API-first:** Deploy the scorer as a serverless function (Cloudflare Workers or AWS Lambda). No webcam capture needed — pure weather-based prediction.
2. **Community webcams:** Users in each city submit their favorite sunset-facing webcam YouTube streams. The capture pipeline works unchanged.
3. **Target cities:** Start with Mediterranean coast (Barcelona, Athens, Dubrovnik), then US West Coast (LA, SF, San Diego), then Southeast Asia (Bali, Phuket).

**Moat:** The calibration data. Every day of predict-capture-rate data makes the model better for that city. A competitor can copy the algorithm but not the months of ground truth.

---

## 4. Community Calibration Flywheel

**What:** Users submit sunset photos with their own 1-10 rating. This creates a human ground truth dataset that improves the scoring model.

**Why it matters:** The biggest weakness of the current system is that calibration depends on one person's ratings and a handful of webcam angles. Community input turns this from a solo project into a data flywheel.

**How it works:**
- After each sunset, the app prompts: "How was tonight's sunset? Rate 1-10 and share a photo"
- Photos are Vision AI-rated automatically, creating a three-way comparison: model prediction vs. AI rating vs. human rating
- Aggregate human ratings per city to detect systematic model biases (e.g., "the model consistently overrates clear-sky sunsets in Barcelona")
- Periodically retune weights using the accumulated dataset

**Flywheel effect:** Better predictions attract more users. More users submit more ratings. More ratings improve predictions. This is the defensible loop.

---

## What I'd Build Next

If I had one weekend: the Instagram bot. It's the lowest-effort, highest-visibility feature, and it creates a public artifact that markets itself.

If I had a month: the push notification PWA with multi-city support. That's the version that could actually become a small product.
