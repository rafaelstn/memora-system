import re

from app.core.assistant import DEEP_REASONING_PATTERNS


def test_deep_reasoning_detection():
    assert DEEP_REASONING_PATTERNS.search("Explica a arquitetura")
    assert DEEP_REASONING_PATTERNS.search("como funciona o sistema")
    assert DEEP_REASONING_PATTERNS.search("por que isso acontece")
    assert DEEP_REASONING_PATTERNS.search("analisa esse código")
    assert DEEP_REASONING_PATTERNS.search("compara as duas funções")


def test_simple_query_not_detected():
    assert not DEEP_REASONING_PATTERNS.search("quais funções existem")
    assert not DEEP_REASONING_PATTERNS.search("lista os endpoints")
    assert not DEEP_REASONING_PATTERNS.search("o que é a variável X")
