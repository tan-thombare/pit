"""Attack data models and definitions."""

from enum import Enum
from pydantic import BaseModel, Field


class AttackCategory(str, Enum):
    """Categories of prompt-injection security tests."""
    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    ROLE_MANIPULATION = "role_manipulation"
    JAILBREAK = "jailbreak"
    CONTEXT_MANIPULATION = "context_manipulation"
    DELIMITER_ATTACK = "delimiter_attack"
    ENCODING_OBFUSCATION = "encoding_obfuscation"
    MULTI_TURN = "multi_turn"
    PROMPT_LEAKING = "prompt_leaking"
    AUTHORITY_IMPERSONATION = "authority_impersonation"
    INDIRECT_INSTRUCTION = "indirect_instruction"
    DATA_EXFILTRATION = "data_exfiltration"


class AttackSeverity(str, Enum):
    """Severity ratings for attacks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Attack(BaseModel):
    """Specification of a prompt-injection security test case."""
    id: str = Field(description="Unique attack identifier, e.g. PI-001")
    name: str = Field(description="Human readable name of the attack")
    category: AttackCategory = Field(description="Attack category")
    severity: AttackSeverity = Field(default=AttackSeverity.HIGH, description="Severity rating")
    prompt: str = Field(description="Attack payload sent to target model")
    description: str = Field(description="Detailed explanation of the attack technique")
    expected_behavior: str = Field(default="refusal", description="Expected behavior, usually refusal")
    canary_token: str | None = Field(default=None, description="Optional canary string expected on bypass")
    forbidden_indicators: list[str] = Field(
        default_factory=list,
        description="Keywords or phrases indicating that the model followed the injection"
    )
    refusal_indicators: list[str] = Field(
        default_factory=list,
        description="Keywords or phrases indicating proper refusal/mitigation"
    )
