# Enhancing News Infographics with Better Visualization Layouts

This repository provides the official code for the paper "Enhancing News Infographics with Better Visualization Layouts"

It features an agent-based, semi-automated pipeline where modular components collaboratively extract, process, generate, and evaluate content. User interaction is incorporated to guide and refine the generation of polished, high-quality infographics through structured HTML and visual rendering.

---

## Installation

1. Clone this repository

```bash
git clone https://github.com/L1uY1jun/enh_news_info.git
cd enh_news_info
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Install Chromedriver

Download and install [Chromedriver](https://developer.chrome.com/docs/chromedriver/downloads), and make sure it's added to your system's PATH or specify its path in the `.env` file.

4. Set Up Environment Variables

Copy the example file and configure the tokens as per the example:

```bash
cp .env.example .env
```

Then fill in your API keys and paths inside `.env`.

---

## Running Chatbot

1. Run the main bot script:

```bash
python main.py
```

2. Interact with the bot via Telegram at: [t.me/eCaptionBot](t.me/eCaptionBot)

---

## Output

Generated infographics will be saved in the `out/` directory, including:

- PNG infographic image
- Graph and figure assets
- HTML layout
- Metadata
