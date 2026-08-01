"""Built-in phrase / synonym / blacklist dictionaries for Defluffer."""

from __future__ import annotations

from typing import TypedDict


class Dictionary(TypedDict, total=False):
    phrases: dict[str, str]
    logic: dict[str, str]
    synonyms: dict[str, str]
    blacklist: list[str]
    guard_sensitive: bool
    dedupe_adjacent_words: bool


SAFE_PHRASES: dict[str, str] = {
    "hello there": "",
    "hi there": "",
    "hello": "",
    "thank you so much": "",
    "thank you": "",
    "thanks a lot": "",
    "thanks": "",
    "if you do not mind": "",
    "if you don't mind": "",
    "i would really appreciate it if you could": "",
    "i would appreciate it if you could": "",
    "i would love it if you could": "",
    "could you please": "",
    "would you please": "",
    "can you please": "",
    "please provide": "provide",
    "please": "",
    "make sure that": "ensure",
    "make sure": "ensure",
    "due to the fact that": "because",
    "owing to the fact that": "because",
    "take into consideration that": "consider",
    "take into account that": "consider",
    "bear in mind that": "note",
    "keep in mind that": "note",
    "at the very end": "end",
    "at the end of the day": "",
    "act as a": "be",
    "act as an": "be",
    "i am really trying to figure out how to": "I need to",
    "i am trying to figure out how to": "I need to",
    "trying to figure out how to": "need to",
    "figure out how to": "learn to",
    "all of the information": "all information",
    "provide a step by step guide": "provide steps",
    "step by step guide": "steps",
    "step-by-step guide": "steps",
    "in order to": "to",
    "for the purpose of": "to",
    "with the aim of": "to",
    "as soon as possible": "ASAP",
    "let me know if you need anything else": "",
    "feel free to": "",
    "don't hesitate to": "",
    "do not hesitate to": "",
    "no external libraries": "no external libs",
    "without using any external libraries": "without external libs",
    "i was wondering if": "",
    "i was wondering whether": "",
    "it would be great if": "",
    "it would be helpful if": "",
    "kindly": "",
    "i hope this helps": "",
    "looking forward to your response": "",
}

STANDARD_PHRASES: dict[str, str] = {
    **SAFE_PHRASES,
    "greater than or equal to": ">=",
    "less than or equal to": "<=",
    "strictly equals to": "===",
    "strictly equal to": "===",
    "is equal to": "=",
    "is not equal to": "!=",
    "not equal to": "!=",
    "the application is": "app is",
    "the results are": "results are",
    "the output should be": "output must be",
    "it is required that you": "you must",
    "it is necessary that you": "you must",
    "you are required to": "you must",
    "currently in the production environment": "in production",
    "in the production environment": "in production",
    "standard JSON object": "JSON object",
    "utilize": "use",
    "utilizing": "using",
    "utilizes": "uses",
    "a large number of": "many",
    "a number of": "some",
    "in the event that": "if",
    "in the case that": "if",
    "with regard to": "about",
    "with respect to": "about",
    "in terms of": "for",
    "prior to": "before",
    "subsequent to": "after",
    "in addition to": "besides",
    "as well as": "and",
    "in spite of": "despite",
    "on the other hand": "however",
    "by means of": "via",
    "for the reason that": "because",
    "the fact that": "that",
    "has the ability to": "can",
    "is able to": "can",
    "is capable of": "can",
    "um": "",
    "uh": "",
    "yeah so": "",
    "like": "",
    "can you, can you please": "",
    "basically basically": "",
    "i just need": "I need",
    "i just want": "I want",
}

LOGIC: dict[str, str] = {
    "greater than": ">",
    "less than": "<",
}

SAFE_SYNONYMS: dict[str, str] = {
    "configurations": "configs",
    "configuration": "config",
    "parameters": "params",
    "parameter": "param",
    "microservice": "service",
    "microservices": "services",
}

STANDARD_SYNONYMS: dict[str, str] = {
    **SAFE_SYNONYMS,
    "application": "app",
    "applications": "apps",
    "database": "DB",
    "databases": "DBs",
    "repository": "repo",
    "repositories": "repos",
    "environment": "env",
    "environments": "envs",
    "information": "info",
    "function": "fn",
    "functions": "fns",
    "javascript": "JS",
    "typescript": "TS",
    "python": "Python",
    "kubernetes": "Kubernetes",
    "documentation": "docs",
    "requirements": "reqs",
    "approximately": "approx",
}

BLACKLIST: list[str] = [
    "really",
    "basically",
    "actually",
    "simply",
    "just",
    "quite",
    "rather",
    "somewhat",
    "very",
    "literally",
    "honestly",
    "obviously",
    "clearly",
    "definitely",
    "absolutely",
    "totally",
    "pretty",
    "kinda",
    "sorta",
]

SAFE: Dictionary = {
    "phrases": SAFE_PHRASES,
    "logic": {},
    "synonyms": SAFE_SYNONYMS,
    "blacklist": BLACKLIST,
    "guard_sensitive": False,
    "dedupe_adjacent_words": False,
}

STANDARD: Dictionary = {
    "phrases": STANDARD_PHRASES,
    "logic": LOGIC,
    "synonyms": STANDARD_SYNONYMS,
    "blacklist": BLACKLIST,
    "guard_sensitive": True,
    "dedupe_adjacent_words": True,
}

PROFILES: dict[str, Dictionary] = {
    "safe": SAFE,
    "standard": STANDARD,
    "standardGuardedDedupe": STANDARD,
}
