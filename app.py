import streamlit as st
import pandas as pd
import plotly.express as px
import os
from translations import Translator

from simulation import (
    generate_party_personas, generate_agents_personas,
    get_opinions, form_question, agent_vote,
    get_current_parliament_distribution, set_api_key
)


def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'simulation_complete' not in st.session_state:
        st.session_state.simulation_complete = False
    if 'parties' not in st.session_state:
        st.session_state.parties = None
    if 'agents' not in st.session_state:
        st.session_state.agents = None
    if 'question' not in st.session_state:
        st.session_state.question = None
    if 'votes' not in st.session_state:
        st.session_state.votes = None
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = bool(os.getenv("OPENAI_API_KEY"))
    if 'language' not in st.session_state:
        st.session_state.language = 'en'
    if 'translator' not in st.session_state:
        st.session_state.translator = Translator(st.session_state.language)


def create_party_chart(parties, t):
    """Create a pie chart of party distribution"""
    df = pd.DataFrame(parties)
    fig = px.pie(
        df,
        values='seats',
        names='name',
        title=t.get("charts.party_distribution"),
        hole=0.4
    )
    return fig


def create_vote_chart(votes, t):
    """Create a bar chart of voting results"""
    yes_count = votes.count("Yes")
    no_count = votes.count("No")
    df = pd.DataFrame({
        'Vote': [t.get("voting.yes"), t.get("voting.no")],
        'Count': [yes_count, no_count]
    })
    fig = px.bar(
        df,
        x='Vote',
        y='Count',
        title=t.get("voting.results"),
        color='Vote',
        color_discrete_map={t.get("voting.yes"): 'green', t.get("voting.no"): 'red'}
    )

    # Update the axis titles after creating the chart
    fig.update_layout(
        yaxis_title=t.get("charts.vote_count"),
        xaxis_title=t.get("charts.vote_label")
    )

    return fig


def run_simulation():
    """Run the parliamentary simulation"""
    t = st.session_state.translator

    with st.spinner(t.get('init_simulation')):
        # Get initial distribution
        distribution = get_current_parliament_distribution()

        # Generate party personas
        st.session_state.parties = generate_party_personas(
            distribution,
            st.session_state.issue
        )

        # Create and display party distribution chart
        party_chart = create_party_chart(st.session_state.parties, t)
        st.plotly_chart(party_chart, use_container_width=True, key="party_distribution_chart")

        # Generate agent personas and opinions
        st.session_state.agents = generate_agents_personas(
            st.session_state.parties,
            st.session_state.issue
        )
        opinions = get_opinions(st.session_state.agents, st.session_state.issue)

        # Form question and get votes
        st.session_state.question = form_question(opinions, st.session_state.issue)
        agent_vote(st.session_state.agents, opinions, st.session_state.question)

        # Store votes
        st.session_state.votes = [a["vote"] for a in st.session_state.agents]

        st.session_state.simulation_complete = True


def main():
    # Page config
    st.set_page_config(
        page_title="AI Parliament",
        page_icon="🏛️",
        layout="wide"
    )

    # Initialize session state
    initialize_session_state()

    t = st.session_state.translator

    # Language selector in sidebar
    languages = {'en': 'English', 'it': 'Italiano'}
    selected_lang = st.sidebar.selectbox(
        'Language/Lingua',
        options=list(languages.keys()),
        format_func=lambda x: languages[x],
        key='language_selector'
    )

    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.translator = Translator(selected_lang)
        st.rerun()

    st.title("🏛️ " + t.get("page_title"))
    st.markdown(t.get("app_description"))

    if not st.session_state.api_key_set:
        api_key = st.text_input(t.get("api_key_prompt"), type="password")
        if api_key:
            set_api_key(api_key)
            st.session_state.api_key_set = True
        else:
            st.warning(t.get("api_key_missing"))
            return

    # Input section
    with st.form("simulation_form"):
        issue = st.text_input(
            t.get("debate_input"),
            placeholder=t.get("debate_placeholder")
        )
        submitted = st.form_submit_button(t.get("start_button"))

        if submitted and issue:
            st.session_state.issue = issue
            st.session_state.simulation_complete = False

    # Run simulation if issue is provided
    if hasattr(st.session_state, 'issue') and not st.session_state.simulation_complete:
        run_simulation()

    # Display results if simulation is complete
    if st.session_state.simulation_complete:
        # Create tabs for different sections
        parties_tab, opinions_tab, voting_tab = st.tabs([
            t.get("tabs.parties"),
            t.get("tabs.opinions"),
            t.get("tabs.voting")
        ])

        with parties_tab:
            st.subheader(t.get("party_info"))
            cols = st.columns(2)

            # Party distribution chart
            with cols[0]:
                party_chart = create_party_chart(st.session_state.parties, t)
                st.plotly_chart(party_chart, use_container_width=True)

            # Party details
            with cols[1]:
                for party in st.session_state.parties:
                    with st.expander(f"{party['name']} ({party['seats']} seats)"):
                        st.write(party['persona'])

        with opinions_tab:
            st.subheader(t.get("representatives"))

            # Create columns for better organization
            for i in range(0, len(st.session_state.agents), 2):
                cols = st.columns(2)

                # First agent in row
                with cols[0]:
                    agent = st.session_state.agents[i]
                    st.markdown(f"**{t.get('agent')} {i + 1} ({agent['party_name']})**")
                    st.write(agent['opinion'])

                # Second agent in row (if exists)
                if i + 1 < len(st.session_state.agents):
                    with cols[1]:
                        agent = st.session_state.agents[i + 1]
                        st.markdown(f"**{t.get('agent')} {i + 2} ({agent['party_name']})**")
                        st.write(agent['opinion'])

        with voting_tab:
            st.subheader(t.get("voting.results"))

            # Display the question
            st.markdown("### " + t.get("voting.question"))
            st.write(st.session_state.question)

            cols = st.columns(2)

            # Voting results chart
            with cols[0]:
                vote_chart = create_vote_chart(st.session_state.votes, t)
                st.plotly_chart(vote_chart, use_container_width=True, key="voting_results_chart")

            # Individual votes
            with cols[1]:
                st.markdown("### " + t.get("voting.individual"))
                for i, agent in enumerate(st.session_state.agents):
                    vote_color = "🟢" if agent['vote'] == "Yes" else "🔴"
                    st.write(f"{vote_color} {t.get('agent')} {i + 1} ({agent['party_name']}): {agent['vote']}")

            # Final result
            yes_count = st.session_state.votes.count("Yes")
            no_count = st.session_state.votes.count("No")
            result = t.get("voting.passed") if yes_count > no_count else t.get("voting.failed")
            st.markdown(f"### {t.get('voting.final')}: {result}")
            st.progress(yes_count / len(st.session_state.votes))
            st.write(t.get("voting.yes_votes").format(
                yes_count,
                f"{yes_count / len(st.session_state.votes) * 100:.1f}"
            ))
            st.write(t.get("voting.no_votes").format(
                no_count,
                f"{no_count / len(st.session_state.votes) * 100:.1f}"
            ))


if __name__ == "__main__":
    main()