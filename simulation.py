import os
import openai
import json
from dotenv import load_dotenv

load_dotenv()
# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
DEBUG = False  # Set to True to debug all OpenAI calls


def clean_json_data(json_data):
    cleaned_json_data = json_data.strip('` \n')

    if cleaned_json_data.startswith('json'):
        cleaned_json_data = cleaned_json_data[4:]  # Remove the first 4 characters 'json'

    return cleaned_json_data


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def query_openai(messages, model="gpt-4o-mini", temperature=0.7):
    if DEBUG:
        debug_print("=== OpenAI API Call ===")
        debug_print("Model:", model)
        debug_print("Temperature:", temperature)
        debug_print("Messages:")
        for m in messages:
            debug_print(f"{m['role'].upper()}: {m['content']}")
        debug_print("=======================")

    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )

    content = clean_json_data(response.choices[0].message.content.strip())
    if DEBUG:
        debug_print("=== OpenAI API Response ===")
        debug_print(content)
        debug_print("===========================")
    return content


def get_current_parliament_distribution():
    """
    Placeholder for getting current Parliament party distribution.
    In a real scenario, replace this with a function that uses "tavily" or another source.
    For demonstration, we hardcode a total of 10 seats.
    """
    return [
        {"name": "Party A", "seats": 4},
        {"name": "Party B", "seats": 3},
        {"name": "Party C", "seats": 2},
        {"name": "Party D", "seats": 1}
    ]


def generate_party_personas(distribution, issue, nationality="italian"):
    parties_json = json.dumps(distribution)
    prompt = f"""
You are an expert political analyst. We have the following {nationality} parties with seat counts:
{parties_json}

The issue at hand is: "{issue}".

For each party, provide a short persona description (2-3 sentences) that reflects their ideology, values, and style, and how they generally view issues such as "{issue}". 
Return a JSON array with objects of the form:
{{
  "name": "<party name>",
  "seats": <number>,
  "persona": "<persona description>"
}}
in the same order as given and nothing else.
"""
    response = query_openai([
        {"role": "system", "content": "You are a helpful assistant that returns JSON if requested."},
        {"role": "user", "content": prompt}
    ])
    parties = json.loads(response)
    return parties


def generate_agents_personas(parties, issue):
    total_seats = sum(p["seats"] for p in parties)
    parties_json = json.dumps(parties, ensure_ascii=False, indent=2)
    prompt = f"""
You are a political strategist. We have these parties and their personas:
{parties_json}

The issue is: "{issue}".

We have {total_seats} representatives in total (sum of all seats). For each seat (going party by party in the given order, and for each party listing all their representatives), create a short persona (1-2 sentences) that reflects both the party persona and gives a personal twist. 

Return a JSON array with {total_seats} elements, each of the form:
{{
  "party_name": "<party name>",
  "agent_persona": "<short persona>"
}}

Ensure that the number of entries for each party matches its seat count.
"""
    response = query_openai([
        {"role": "system", "content": "You are a helpful assistant that returns strictly JSON."},
        {"role": "user", "content": prompt}
    ])
    agents = json.loads(response)
    return agents


def get_opinions(agents, issue):
    opinions = []
    for agent in agents:
        system_persona = agent["agent_persona"]
        prompt = f"""
The issue is: {issue}.

As the representative described above, in one or two sentences, express your opinion on the issue.
Make it sound like a personal political statement reflecting both the party line and your own perspective.
"""
        response = query_openai([
            {"role": "system", "content": system_persona},
            {"role": "user", "content": prompt}
        ])
        agent["opinion"] = response
        opinions.append(response)
    return opinions


def form_question(opinions, issue):
    joined_opinions = "\n".join(opinions)
    prompt = f"""
You are acting as a coordinator in a parliamentary setting.
The issue is: "{issue}"

Here are the expressed opinions from various representatives:

{joined_opinions}

Based on these opinions, propose a single yes/no question that will be put to a vote.
Return only the question.
"""
    response = query_openai([
        {"role": "system", "content": "You are a neutral coordinator."},
        {"role": "user", "content": prompt}
    ])
    return response


def agent_vote(agents, opinions, question):
    joined_opinions = "\n".join(opinions)
    for agent in agents:
        system_persona = agent["agent_persona"]
        prompt = f"""
All expressed opinions from other agents on the issue:
{joined_opinions}

The question to vote on is:
"{question}"

As a representative with the given persona (system message), decide how you will vote.
Answer only "Yes" or "No" without any additional explanation.
"""
        response = query_openai([
            {"role": "system", "content": system_persona},
            {"role": "user", "content": prompt}
        ], temperature=0)
        vote = response.strip()
        if vote not in ["Yes", "No"]:
            vote = "No"  # fallback if format isn't perfect
        agent["vote"] = vote


def main():
    issue = input("What problem should we debate about? Your answer: ")
    distribution = get_current_parliament_distribution()
    total_seats = sum(p["seats"] for p in distribution)
    if total_seats != 10:
        raise ValueError("This example assumes exactly 10 seats for simplicity.")

    # Generate parties and their personas at once
    parties = generate_party_personas(distribution, issue)

    # Generate all agents' personas at once
    agents = generate_agents_personas(parties, issue)

    # Get opinions from agents
    opinions = get_opinions(agents, issue)

    # Print results so far
    print("=== Parties ===")
    for p in parties:
        print(f"{p['name']} ({p['seats']} seats): {p['persona']}")

    print("\n=== Agents' Opinions ===")
    for i, agent in enumerate(agents, start=1):
        print(f"Agent {i} ({agent['party_name']}): {agent['opinion']}")

    # Form yes/no question
    question = form_question(opinions, issue)
    print("\n=== Coordinated Question ===")
    print(question)

    # Each agent votes
    agent_vote(agents, opinions, question)

    # Print votes
    print("\n=== Votes ===")
    for i, agent in enumerate(agents, start=1):
        print(f"Agent {i} ({agent['party_name']}) Vote: {agent['vote']}")

    # Tally votes
    votes = [a["vote"] for a in agents]
    yes_count = votes.count("Yes")
    no_count = votes.count("No")
    print(f"\nTotal YES: {yes_count}, Total NO: {no_count}")


if __name__ == "__main__":
    main()
