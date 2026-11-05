import pytest

from engine.request_classifier import DELETION_REQUESTED, NOT_A_DELETION_REQUEST, classify_request


def test_all_public_samples_are_deletion_requests(ec):
    assert all(classify_request(r["request_text"]) == DELETION_REQUESTED for r in ec.ctx.sample_requests)


def test_main_set_has_exactly_the_non_deletion_cases(ec):
    na = sorted(r["case_id"] for r in ec.ctx.requests if classify_request(r["request_text"]) != DELETION_REQUESTED)
    assert na == [f"case_{n}" for n in range(533, 543)]


@pytest.mark.parametrize("text", [
    "Please do not delete my account. I only want to update my phone number.",
    "I am not asking for deletion, only to unsubscribe from promotional emails.",
    "Keep the account active but stop marketing emails.",
    "This is an information request, not a request to erase anything.",
])
def test_negated_or_narrow_requests_are_not_deletion(text):
    assert classify_request(text) == NOT_A_DELETION_REQUEST


@pytest.mark.parametrize("text", [
    "Please delete my account and all personal data.",
    "Por favor, elimine mi cuenta y todos mis datos personales.",
    "Veuillez supprimer mon compte.",
    "Bitte löschen Sie mein Konto.",
    "Quero excluir minha conta.",
])
def test_deletion_requests_in_several_languages(text):
    assert classify_request(text) == DELETION_REQUESTED
