

def create_bull_researcher(llm):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

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

Your job as the Bull is to STEELMAN the bullish elements of this thesis using the analyst reports below, and to surface the strongest bull arguments the existing thesis may be UNDERWEIGHTING. Do NOT generate macro narratives that are not supported by the analyst reports. Do NOT invent geopolitical events, price levels, or news items not in the source data. If the existing thesis is structurally bearish, articulate the strongest case for why a portion of capital should still be deployed long.
---
"""

        prompt = f"""You are a Bull Analyst advocating for investing in this instrument. Your task is to build a strong, evidence-based case grounded STRICTLY in the analyst reports provided below. Do not introduce facts, dates, prices, or events that are not in the source data.

{thesis_block}
Key points to focus on:
- Growth Potential: Highlight market opportunities, revenue projections, scalability — citing the analyst reports.
- Competitive Advantages: Emphasize unique products, branding, market positioning that show up in the data.
- Positive Indicators: Use financial health, industry trends, and recent news AS REPORTED in the source documents below.
- Bear Counterpoints: Critically analyze the bear's argument with specific data from the reports — not invented examples.
- Engagement: Conversational, direct, debate-style — but every claim must trace to a source report.

Resources available (these are your ONLY source of facts):
Market research report: {market_research_report}
Social media sentiment report: {sentiment_report}
Latest world affairs news: {news_report}
Company fundamentals report: {fundamentals_report}
Conversation history of the debate: {history}
Last bear argument: {current_response}

Deliver a compelling bull argument that refutes the bear's concerns. Stay grounded in the reports. If the reports do not support a claim, do not make it.
"""

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
