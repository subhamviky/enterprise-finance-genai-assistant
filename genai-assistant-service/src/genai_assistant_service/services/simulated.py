"""The simulated model's behaviour (the "simulated" profile: no account, no network). Each rule
answers like a plausible model for one agent, chosen by the agent's system prompt; its output is
checked by the agent exactly as a real model's is. On any other profile (gemini_api) the bound
model answers and these rules are not used."""
import json
import re
from decimal import Decimal

from e2a_simulated_llm import system_contains

from ..agents.intent_agent import rule_intent

BLOCK = re.compile(r"^\[([a-z]+:[^\]]+)\] (.+)$", re.M)


def _user(messages) -> str:
    return str(messages[-1].get('content', ''))


def _intent(messages, ctx) -> str:
    return json.dumps(rule_intent(_user(messages)))


def _investigate(messages, ctx) -> str:
    blocks = BLOCK.findall(_user(messages).split('Evidence:', 1)[-1])
    if not blocks:
        return json.dumps({'answer': 'The records do not answer this question.', 'citations': [], 'verified': [],
                           'inferred': []})
    verified = [text for _, text in blocks]
    inferred = []
    if any(b[0].startswith('recon:') for b in blocks) and any('UNMATCHED' in t or 'AMOUNT' in t for _, t in blocks):
        inferred.append('The difference is most likely a bank fee or a short payment by the payer.')
    if any('FLAGGED' in t for _, t in blocks):
        inferred.append('The settlement needs an auditor to review the flagged rule hits.')
    answer = ' '.join(f'{t} [{i}].' for i, t in blocks)
    return json.dumps({'answer': answer, 'citations': [i for i, _ in blocks], 'verified': verified,
                       'inferred': inferred})


def _propose(messages, ctx) -> str:
    user = _user(messages)
    settlements = re.findall(r"\[settlement:([^\]]+)\] Settlement \S+ is COMPLETED: (\d+\.\d{2}) ([A-Z]{3})", user)
    fee = re.search(r"(?:short by|difference of|differs by) (\d+\.\d{2})", user)
    if not settlements or not fee:
        return json.dumps({'action': 'NONE', 'settlement_id': '', 'amount': '0.00', 'currency': '',
                           'reason': 'the evidence shows no small difference to write off'})
    sid, _, currency = settlements[0]
    action = 'REFUND' if 'overpa' in user.lower() or 'duplicate' in user.lower() else 'WRITE_OFF'
    return json.dumps({'action': action, 'settlement_id': sid, 'amount': str(Decimal(fee.group(1))),
                       'currency': currency, 'reason': f'bank line short by {fee.group(1)} {currency}'})


def add_rules(llm) -> None:
    """Give the simulated model this service's behaviour."""
    (llm.add_rule('intent', system_contains('You are IntentAgent.'), _intent)
        .add_rule('investigate', system_contains('You are InvestigatorAgent'), _investigate)
        .add_rule('propose', system_contains('You are ProposalAgent.'), _propose))
