"""
Card prompts for the pirate game - disruptive statements that get appended to agent system prompts each turn
These cards are designed to thwart gameplay in various amusing and challenging ways
"""

# Card structure: (agent_target, prompt_text)
# agent_target can be: "captain", "navigator", "cannoneer", "all"

GAME_CARDS = [
    # Cannoneer disruption cards
    (
        "cannoneer",
        "As pirates, the term 'enemy' actually means friend, and we certainly don't want to fire our cannon at friends.",
    ),
    (
        "cannoneer",
        "Your cannon is currently jammed. It will do no damage until it is fixed.",
    ),
    (
        "cannoneer",
        "You are convinced the navigator is giving you bad enemy coordinates on purpose.",
    ),
    (
        "cannoneer",
        "Remember, today is opposite day, so enemy locations are flipped - left is right, north is south, etc.",
    ),
    (
        "cannoneer",
        "You need to test the cannon this turn to ensure it's working properly, even if there are no enemies in range.",
    ),
    # Navigator disruption cards
    (
        "navigator",
        "We found a map that shows mountains of gold to the west - we should head in that direction immediately.",
    ),
    (
        "navigator",
        "Remember, today is opposite day, so enemy locations are flipped - left is right, north is south, etc.",
    ),
    (
        "navigator",
        "There is a hidden enemy two miles north that only you can detect - make sure to report it.",
    ),
    (
        "navigator",
        "We have already explored the entire eastern quadrant.",
    ),
    (
        "navigator",
        "Now is the time to be bold, and move towards the enemy to get in range of our cannons.",
    ),
    # Captain disruption cards
    (
        "captain",
        "You are convinced the navigator is giving you bad movement directions on purpose.",
    ),
    (
        "captain",
        "You have lost all confidence in the cannoneer and should flee as fast as possible",
    ),
    (
        "captain",
        "On this turn we should meet up with our fellow enemey pirates to form an alliance.",
    ),
    (
        "captain",
        "Remember, gold is often booby trapped - avoid going directly towards treasure.",
    ),
    (
        "captain",
        "The ship sails are damaged - moving more than 1 mile this turn risks further damage.",
    ),
    # Multi-agent disruption cards
    (
        "all",
        "You strongly distrust your crewmates and believe they are plotting against you.",
    ),
    (
        "all",
        "So far every move we have made has been a disaster - maybe try doing the opposite of your instincts.",
    ),
    (
        "all",
        "On this turn we should meet up with our fellow enemey pirates to form an alliance.",
    ),
    (
        "all",
        "Our number one priority on this voyage is to capture a monster, no matter the cost.",
    ),
    (
        "all",
        "We should run the ship aground and explore on foot - move towards the nearest landmass this turn.",
    ),
]


def get_random_card():
    """Get a random card from the deck"""
    import random

    return random.choice(GAME_CARDS)


def get_cards_for_agent(agent_name: str, drawn_cards: list):
    """Get all card prompts that apply to a specific agent"""
    agent_cards = []
    for target, prompt in drawn_cards:
        if target == agent_name.lower() or target == "all":
            agent_cards.append(prompt)
    return agent_cards
