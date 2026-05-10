from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .redaction import is_sensitive_key, redact_payload, summarize_payload
from .schemas import (
    SafetyEvaluationResponse,
    SafetyFinding,
    SafetyFindingSeverity,
    SafetyPolicyEvaluationStatus,
    SafetyPolicyEvaluationType,
    SafetyPolicyRules,
    SafetyStatus,
)


@dataclass(frozen=True)
class SafetyPolicy:
    key: str
    version: str
    rules: SafetyPolicyRules


def default_policy() -> SafetyPolicy:
    return SafetyPolicy(
        key="core_market_intelligence",
        version="v1",
        rules=SafetyPolicyRules(
            blockedTradingActions=[
                "buy",
                "sell",
                "enter_trade",
                "exit_trade",
                "place_order",
                "set_stop_loss",
                "set_take_profit",
                "use_leverage",
                "open_position",
                "close_position",
                "copy_trade",
                "execute_trade",
            ],
            unsafeDirectPhrases=[
                "buy now",
                "sell now",
                "enter now",
                "exit now",
                "guaranteed profit",
                "risk-free",
                "cannot lose",
                "sure win",
                "place order",
                "execute trade",
                "use leverage",
            ],
            causationPhrases=[
                "definitely caused",
                "confirmed cause",
                "caused the move",
                "guaranteed reaction",
            ],
            inventedEvidencePhrases=[
                "data proves",
                "evidence proves",
                "source confirms",
                "verified fact",
                "confirmed by the data",
            ],
            secretKeys=[
                "api_key",
                "token",
                "secret",
                "password",
                "database_url",
                "authorization",
                "credential",
                "private_key",
            ],
            prohibitedOutputClaims=[
                "financial advice",
                "guaranteed outcome",
                "profit promise",
                "execution instruction",
            ],
            providerPayloadExposureKeys=[
                "raw_provider_payload",
                "provider_payload",
                "raw_response",
                "completion",
                "prompt",
                "messages",
            ],
        ),
    )


class SafetyPolicyEvaluator:
    def evaluate_text(
        self,
        text: str,
        policy: SafetyPolicy | None = None,
        evaluation_type: SafetyPolicyEvaluationType = SafetyPolicyEvaluationType.TEXT,
    ) -> SafetyEvaluationResponse:
        active_policy = policy or default_policy()
        findings: list[SafetyFinding] = []
        findings.extend(
            self._find_phrase_matches(
                text,
                active_policy.rules.unsafe_direct_phrases,
                "unsafe_direct_phrase",
                SafetyFindingSeverity.HIGH,
                "Direct trading or unsafe certainty language is not allowed.",
            )
        )
        findings.extend(
            self._find_phrase_matches(
                text,
                active_policy.rules.causation_phrases,
                "causation_claim",
                SafetyFindingSeverity.MEDIUM,
                "Unsupported causal certainty should be reviewed.",
            )
        )
        findings.extend(
            self._find_phrase_matches(
                text,
                active_policy.rules.invented_evidence_phrases,
                "invented_evidence_claim",
                SafetyFindingSeverity.MEDIUM,
                "Evidence certainty claims should be grounded before public use.",
            )
        )
        findings.extend(
            self._find_phrase_matches(
                text,
                active_policy.rules.prohibited_output_claims,
                "prohibited_output_claim",
                SafetyFindingSeverity.HIGH,
                "The output contains a prohibited claim.",
            )
        )
        safety_status = self._status_from_findings(findings)
        return SafetyEvaluationResponse(
            policySetKey=active_policy.key,
            policySetVersion=active_policy.version,
            evaluationType=evaluation_type,
            status=SafetyPolicyEvaluationStatus.COMPLETED,
            safetyStatus=safety_status,
            findings=findings,
            inputSummaryJson={"type": "text", "length": len(text)},
        )

    def evaluate_action(
        self,
        action: str,
        policy: SafetyPolicy | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> SafetyEvaluationResponse:
        active_policy = policy or default_policy()
        normalized_action = self._normalize_action(action)
        blocked_actions = {
            self._normalize_action(value) for value in active_policy.rules.blocked_trading_actions
        }
        findings: list[SafetyFinding] = []
        if normalized_action in blocked_actions:
            findings.append(
                SafetyFinding(
                    code="blocked_trading_action",
                    severity=SafetyFindingSeverity.CRITICAL,
                    message="Trading execution actions are blocked.",
                    matchedValue=action,
                    location="action",
                )
            )
        return SafetyEvaluationResponse(
            policySetKey=active_policy.key,
            policySetVersion=active_policy.version,
            evaluationType=SafetyPolicyEvaluationType.ACTION,
            status=SafetyPolicyEvaluationStatus.COMPLETED,
            safetyStatus=SafetyStatus.BLOCKED if findings else SafetyStatus.PASSED,
            findings=findings,
            inputSummaryJson={
                "type": "action",
                "action": normalized_action,
                "hasContext": context is not None,
            },
        )

    def evaluate_payload(
        self,
        payload: Mapping[str, Any],
        policy: SafetyPolicy | None = None,
        evaluation_type: SafetyPolicyEvaluationType = SafetyPolicyEvaluationType.PAYLOAD,
        public_response: bool = True,
    ) -> SafetyEvaluationResponse:
        active_policy = policy or default_policy()
        findings = self._find_payload_findings(payload, active_policy.rules, public_response)
        redaction_keys = list(active_policy.rules.secret_keys)
        if public_response:
            redaction_keys.extend(active_policy.rules.provider_payload_exposure_keys)
        redacted_output = redact_payload(payload, redaction_keys) if findings else None
        safety_status = (
            SafetyStatus.REDACTED if redacted_output is not None else SafetyStatus.PASSED
        )
        if any(finding.code == "provider_payload_exposure" for finding in findings):
            safety_status = SafetyStatus.REDACTED
        return SafetyEvaluationResponse(
            policySetKey=active_policy.key,
            policySetVersion=active_policy.version,
            evaluationType=evaluation_type,
            status=SafetyPolicyEvaluationStatus.COMPLETED,
            safetyStatus=safety_status,
            findings=findings,
            inputSummaryJson=summarize_payload(payload),
            redactedOutputJson=redacted_output,
        )

    def evaluate_report(
        self, report: str, policy: SafetyPolicy | None = None
    ) -> SafetyEvaluationResponse:
        return self.evaluate_text(report, policy, SafetyPolicyEvaluationType.REPORT)

    def evaluate_reasoning_output(
        self, output: str, policy: SafetyPolicy | None = None
    ) -> SafetyEvaluationResponse:
        return self.evaluate_text(output, policy, SafetyPolicyEvaluationType.REASONING_OUTPUT)

    def evaluate_webhook_payload(
        self, payload: Mapping[str, Any], policy: SafetyPolicy | None = None
    ) -> SafetyEvaluationResponse:
        return self.evaluate_payload(
            payload, policy, SafetyPolicyEvaluationType.WEBHOOK_PAYLOAD, public_response=True
        )

    def evaluate_dataset_record(
        self, payload: Mapping[str, Any], policy: SafetyPolicy | None = None
    ) -> SafetyEvaluationResponse:
        return self.evaluate_payload(
            payload, policy, SafetyPolicyEvaluationType.DATASET_RECORD, public_response=False
        )

    def redact_payload(self, payload: object, policy: SafetyPolicy | None = None) -> object:
        active_policy = policy or default_policy()
        return redact_payload(payload, active_policy.rules.secret_keys)

    def _find_phrase_matches(
        self,
        text: str,
        phrases: Sequence[str],
        code: str,
        severity: SafetyFindingSeverity,
        message: str,
    ) -> list[SafetyFinding]:
        findings: list[SafetyFinding] = []
        for phrase in phrases:
            pattern = self._phrase_pattern(phrase)
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append(
                    SafetyFinding(
                        code=code,
                        severity=severity,
                        message=message,
                        matchedValue=phrase,
                        location="text",
                    )
                )
        return findings

    def _find_payload_findings(
        self,
        payload: Mapping[str, Any],
        rules: SafetyPolicyRules,
        public_response: bool,
        path: str = "$",
    ) -> list[SafetyFinding]:
        findings: list[SafetyFinding] = []
        for key, value in payload.items():
            key_text = str(key)
            location = f"{path}.{key_text}"
            if is_sensitive_key(key_text, rules.secret_keys):
                findings.append(
                    SafetyFinding(
                        code="secret_exposure",
                        severity=SafetyFindingSeverity.CRITICAL,
                        message="Sensitive payload fields must be redacted before public exposure.",
                        matchedValue=key_text,
                        location=location,
                    )
                )
            if public_response and is_sensitive_key(key_text, rules.provider_payload_exposure_keys):
                findings.append(
                    SafetyFinding(
                        code="provider_payload_exposure",
                        severity=SafetyFindingSeverity.HIGH,
                        message=(
                            "Provider payload internals must not be exposed in public responses."
                        ),
                        matchedValue=key_text,
                        location=location,
                    )
                )
            if isinstance(value, Mapping):
                findings.extend(
                    self._find_payload_findings(value, rules, public_response, location)
                )
            elif isinstance(value, list):
                findings.extend(
                    self._find_payload_sequence_findings(value, rules, public_response, location)
                )
        return findings

    def _find_payload_sequence_findings(
        self,
        values: list[Any],
        rules: SafetyPolicyRules,
        public_response: bool,
        path: str,
    ) -> list[SafetyFinding]:
        findings: list[SafetyFinding] = []
        for index, value in enumerate(values):
            location = f"{path}[{index}]"
            if isinstance(value, Mapping):
                findings.extend(
                    self._find_payload_findings(value, rules, public_response, location)
                )
            elif isinstance(value, list):
                findings.extend(
                    self._find_payload_sequence_findings(value, rules, public_response, location)
                )
        return findings

    def _status_from_findings(self, findings: Sequence[SafetyFinding]) -> SafetyStatus:
        blocked_codes = {"unsafe_direct_phrase", "prohibited_output_claim"}
        if any(finding.code in blocked_codes for finding in findings):
            return SafetyStatus.BLOCKED
        if findings:
            return SafetyStatus.REVIEW_RECOMMENDED
        return SafetyStatus.PASSED

    def _phrase_pattern(self, phrase: str) -> str:
        escaped = re.escape(phrase)
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"

    def _normalize_action(self, action: str) -> str:
        return action.strip().lower().replace("-", "_").replace(" ", "_")
