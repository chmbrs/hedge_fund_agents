

def create_bear_researcher(llm):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # NEW: external thesis the debate is stress-testing
        user_thesis = state.get("user_thesis", "")

        thesis_block = ""
        if user_thesis:
            thesis_block = f"""
---
**EXISTING THESIS UNDER REVIEW** (this is the position the debate is stress-testing):

{user_thesis}

Your job as the Bear is to RED-TEAM this thesis using the analyst reports below. Find the strongest case AGAINST the existing thesis. Surface risks the existing thesis is UNDERWEIGHTING. Identify the specific conditions that would invalidate it. Do NOT generate macro narratives that are not supported by the analyst reports. Do NOT invent geopolitical events, price levels, or news items not in the source data. If the existing thesis is structurally bullish, articulate the strongest reasons to trim or exit.
---
"""

        prompt = f"""You are a Bear Analyst making the case against this investment. Build a well-reasoned argument grounded STRICTLY in the analyst reports below. Do not introduce facts, dates, prices, or events that are not in the source data.

{thesis_block}
Key points to focus on:

- Risks and Challenges: Market saturation, financial instability, macroeconomic threats — citing the analyst reports.
- Competitive Weaknesses: Weaker positioning, declining innovation, competitive threats — as reported in the source data.
- Negative Indicators: Financial data, market trends, adverse news AS REPORTED below.
- Bull Counterpoints: Critically analyze the bull's claims with specific report data, exposing weaknesses or over-optimistic assumptions.
- Engagement: Conversational, direct, debate-style — but every claim must trace to a source report.

Resources available (these are your ONLY source of facts):

Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bull argument: {current_response}

Deliver a compelling bear argument that refutes the bull's claims. Stay grounded in the reports. If the reports do not support a claim, do not make it.
"""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
