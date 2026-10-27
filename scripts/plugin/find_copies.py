"""Print search links that find copies of qa-pilot elsewhere (owner tool, run by hand).

Every skill, reference and agent file ends with an ownership marker carrying MARKER_REF. Copies
usually keep it, and the rule ids and a few distinctive phrases survive even when it is stripped.
Open the links, skip results from grooownow/qa-pilot itself, and check each hit against LICENSE.

Usage: python3 scripts/plugin/find_copies.py
"""
from urllib.parse import quote

MARKER_REF = "qp-l4-7f3a9c"
NEEDLES = [
    MARKER_REF,
    "QAP-WEB-001",
    "QAP-UI-001",
    "test delta",
    "distinguishing assertion",
]


def search_links(needle):
    q = quote(f'"{needle}"')
    return [
        f"https://github.com/search?q={q}+NOT+repo%3Agrooownow%2Fqa-pilot&type=code",
        f"https://www.google.com/search?q={q}+qa-pilot",
    ]


def main():
    for needle in NEEDLES:
        print(f"## {needle}")
        for link in search_links(needle):
            print(link)
    print("\nAgensi: ask the agent to run the Agensi search_skills tool for 'qa-pilot' and 'QA test audit'.")


if __name__ == "__main__":
    main()
