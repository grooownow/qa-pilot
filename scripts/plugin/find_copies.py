"""Print search links that find copies of qa-pilot elsewhere (owner tool, run by hand).

Every skill, reference and agent file ends with an ownership marker carrying MARKER_REF. Copies
usually keep it, and the rule ids and a few distinctive phrases survive even when it is stripped.
Open the links, skip results from grooownow/qa-pilot itself, and check each hit against LICENSE.

Usage: python3 scripts/plugin/find_copies.py
"""
from urllib.parse import quote

MARKER_REF = "qp-l4-7f3a9c"
# The marker, rule ids, and full sentences that only qa-pilot uses. Short generic phrases are noise.
NEEDLES = [
    MARKER_REF,
    "QAP-WEB-001",
    "QAP-UI-001",
    "QAP-TC-028",
    "Для каждой сущности с правкой и удалением определено и проверено",
]


def search_links(needle):
    q = quote(f'"{needle}"')
    return [
        f"https://github.com/search?q={q}+-repo%3Agrooownow%2Fqa-pilot&type=code",
        f"https://www.google.com/search?q={q}",
    ]


def main():
    for needle in NEEDLES:
        print(f"## {needle}")
        for link in search_links(needle):
            print(link)
    print("\nAgensi: ask the agent to run the Agensi search_skills tool for 'qa-pilot' and 'QA test audit'.")


if __name__ == "__main__":
    main()
