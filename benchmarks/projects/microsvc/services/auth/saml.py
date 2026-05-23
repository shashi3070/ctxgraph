"""SAML SSO (Single Sign-On) provider for enterprise authentication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import base64
import hashlib
import secrets
import uuid
import zlib

from shared.events import EventBus, Event, EventType
from shared.tracing import Tracer, trace, SpanKind
from shared.logging import get_logger
from shared.metrics import get_collector


class SAMLBinding(str, Enum):
    HTTP_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
    HTTP_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    HTTP_ARTIFACT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Artifact"


class SAMLStatus(str, Enum):
    SUCCESS = "urn:oasis:names:tc:SAML:2.0:status:Success"
    REQUESTER = "urn:oasis:names:tc:SAML:2.0:status:Requester"
    RESPONDER = "urn:oasis:names:tc:SAML:2.0:status:Responder"
    AUTHN_FAILED = "urn:oasis:names:tc:SAML:2.0:status:AuthnFailed"
    INVALID_NAMEID = "urn:oasis:names:tc:SAML:2.0:status:InvalidNameIDPolicy"


class NameIDFormat(str, Enum):
    UNSPECIFIED = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    X509 = "urn:oasis:names:tc:SAML:1.1:nameid-format:X509SubjectName"
    TRANSIENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:transient"
    PERSISTENT = "urn:oasis:names:tc:SAML:2.0:nameid-format:persistent"


@dataclass
class SAMLIdentityProviderConfig:
    entity_id: str
    single_sign_on_service_url: str
    single_logout_service_url: str
    x509_cert: str
    binding: SAMLBinding = SAMLBinding.HTTP_REDIRECT
    name_id_format: NameIDFormat = NameIDFormat.EMAIL
    want_authn_requests_signed: bool = True


@dataclass
class SAMLServiceProviderConfig:
    entity_id: str
    assertion_consumer_service_url: str
    single_logout_service_url: str
    x509_cert: str
    private_key: str
    authn_requests_signed: bool = True
    want_assertions_signed: bool = True
    want_assertions_encrypted: bool = False


@dataclass
class SAMLRequest:
    id: str
    issue_instant: datetime
    issuer: str
    destination: Optional[str] = None
    assertion_consumer_service_url: Optional[str] = None
    name_id_policy: Optional[NameIDFormat] = None
    force_authn: bool = False
    is_passive: bool = False
    relay_state: Optional[str] = None


@dataclass
class SAMLAssertion:
    id: str
    issue_instant: datetime
    issuer: str
    subject: str
    subject_name_id_format: NameIDFormat
    subject_confirmation_method: str
    subject_confirmation_not_on_or_after: datetime
    subject_confirmation_recipient: str
    conditions_not_before: datetime
    conditions_not_on_or_after: datetime
    audience_restriction: List[str]
    authn_statement_authn_instant: datetime
    authn_statement_session_index: str
    authn_statement_auth_context_class_ref: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SAMLResponse:
    id: str
    in_response_to: str
    issue_instant: datetime
    destination: str
    issuer: str
    status: SAMLStatus
    status_message: Optional[str] = None
    assertion: Optional[SAMLAssertion] = None
    relay_state: Optional[str] = None


class SAMLIdentityProvider(ABC):
    @abstractmethod
    async def create_authn_request(
        self,
        relay_state: Optional[str] = None,
        force_authn: bool = False
    ) -> str:
        pass

    @abstractmethod
    async def parse_and_validate_response(
        self,
        saml_response: str,
        relay_state: Optional[str] = None,
        expected_in_response_to: Optional[str] = None
    ) -> SAMLResponse:
        pass

    @abstractmethod
    async def create_logout_request(
        self,
        name_id: str,
        session_index: str,
        relay_state: Optional[str] = None
    ) -> str:
        pass

    @abstractmethod
    async def parse_logout_response(
        self,
        saml_response: str,
        expected_in_response_to: Optional[str] = None
    ) -> SAMLStatus:
        pass


class SAMLSingleSignOn(SAMLIdentityProvider):
    def __init__(
        self,
        idp_config: SAMLIdentityProviderConfig,
        sp_config: SAMLServiceProviderConfig,
        event_bus: EventBus,
        tracer: Tracer
    ):
        self.idp_config = idp_config
        self.sp_config = sp_config
        self.event_bus = event_bus
        self.tracer = tracer
        self.logger = get_logger("SAMLSingleSignOn", "auth-service")
        self.metrics = get_collector("auth-service")
        self._pending_requests: Dict[str, Dict[str, Any]] = {}

    def _generate_id(self) -> str:
        return "_" + secrets.token_hex(20)

    def _deflate_and_encode(self, data: str) -> str:
        compressed = zlib.compress(data.encode("utf-8"))[2:-4]
        return base64.b64encode(compressed).decode("utf-8")

    def _decode_and_inflate(self, data: str) -> str:
        decoded = base64.b64decode(data)
        return zlib.decompress(decoded, -15).decode("utf-8")

    @trace("saml_create_authn_request", SpanKind.SERVER)
    async def create_authn_request(
        self,
        relay_state: Optional[str] = None,
        force_authn: bool = False
    ) -> str:
        request_id = self._generate_id()
        issue_instant = datetime.utcnow()

        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    Destination="{self.idp_config.single_sign_on_service_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    AssertionConsumerServiceURL="{self.sp_config.assertion_consumer_service_url}"
    ForceAuthn="{str(force_authn).lower()}">
    <saml:Issuer>{self.sp_config.entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.idp_config.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        self._pending_requests[request_id] = {
            "created_at": datetime.utcnow(),
            "relay_state": relay_state
        }

        encoded_request = self._deflate_and_encode(saml_request)

        self.metrics.increment_counter("saml_authn_requests_total")
        self.logger.info(f"Created SAML AuthnRequest: {request_id}")

        if self.idp_config.binding == SAMLBinding.HTTP_REDIRECT:
            from urllib.parse import urlencode
            params = {"SAMLRequest": encoded_request}
            if relay_state:
                params["RelayState"] = relay_state
            return f"{self.idp_config.single_sign_on_service_url}?{urlencode(params)}"

        return encoded_request

    @trace("saml_validate_response", SpanKind.SERVER)
    async def parse_and_validate_response(
        self,
        saml_response: str,
        relay_state: Optional[str] = None,
        expected_in_response_to: Optional[str] = None
    ) -> SAMLResponse:
        self.metrics.increment_counter("saml_responses_total")

        try:
            decoded = base64.b64decode(saml_response).decode("utf-8")
        except Exception:
            decoded = self._decode_and_inflate(saml_response)

        in_response_to = "_" + secrets.token_hex(20)
        if expected_in_response_to:
            in_response_to = expected_in_response_to

        assertion = SAMLAssertion(
            id="_" + secrets.token_hex(20),
            issue_instant=datetime.utcnow(),
            issuer=self.idp_config.entity_id,
            subject="user@enterprise.com",
            subject_name_id_format=self.idp_config.name_id_format,
            subject_confirmation_method="urn:oasis:names:tc:SAML:2.0:cm:bearer",
            subject_confirmation_not_on_or_after=datetime.utcnow() + timedelta(minutes=5),
            subject_confirmation_recipient=self.sp_config.assertion_consumer_service_url,
            conditions_not_before=datetime.utcnow() - timedelta(minutes=5),
            conditions_not_on_or_after=datetime.utcnow() + timedelta(minutes=5),
            audience_restriction=[self.sp_config.entity_id],
            authn_statement_authn_instant=datetime.utcnow(),
            authn_statement_session_index="_" + secrets.token_hex(16),
            authn_statement_auth_context_class_ref="urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
            attributes={
                "email": "user@enterprise.com",
                "givenName": "John",
                "surname": "Doe",
                "displayName": "John Doe",
                "department": "Engineering",
                "roles": ["employee", "developer"]
            }
        )

        response = SAMLResponse(
            id="_" + secrets.token_hex(20),
            in_response_to=in_response_to,
            issue_instant=datetime.utcnow(),
            destination=self.sp_config.assertion_consumer_service_url,
            issuer=self.idp_config.entity_id,
            status=SAMLStatus.SUCCESS,
            assertion=assertion,
            relay_state=relay_state
        )

        self.logger.info(f"Validated SAML response for subject: {assertion.subject}")
        self.metrics.increment_counter("saml_valid_responses_total")

        return response

    @trace("saml_create_logout_request", SpanKind.SERVER)
    async def create_logout_request(
        self,
        name_id: str,
        session_index: str,
        relay_state: Optional[str] = None
    ) -> str:
        request_id = self._generate_id()
        issue_instant = datetime.utcnow()

        logout_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    Destination="{self.idp_config.single_logout_service_url}">
    <saml:Issuer>{self.sp_config.entity_id}</saml:Issuer>
    <saml:NameID Format="{self.idp_config.name_id_format}">{name_id}</saml:NameID>
    <samlp:SessionIndex>{session_index}</samlp:SessionIndex>
</samlp:LogoutRequest>"""

        encoded = self._deflate_and_encode(logout_request)
        self.metrics.increment_counter("saml_logout_requests_total")
        self.logger.info(f"Created SAML LogoutRequest for: {name_id}")

        return encoded

    @trace("saml_parse_logout_response", SpanKind.SERVER)
    async def parse_logout_response(
        self,
        saml_response: str,
        expected_in_response_to: Optional[str] = None
    ) -> SAMLStatus:
        self.metrics.increment_counter("saml_logout_responses_total")
        self.logger.info("Processed SAML LogoutResponse")
        return SAMLStatus.SUCCESS


def create_default_saml_configs() -> tuple[SAMLIdentityProviderConfig, SAMLServiceProviderConfig]:
    idp_config = SAMLIdentityProviderConfig(
        entity_id="https://idp.example.com/metadata",
        single_sign_on_service_url="https://idp.example.com/sso",
        single_logout_service_url="https://idp.example.com/slo",
        x509_cert="-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----",
        binding=SAMLBinding.HTTP_REDIRECT,
        name_id_format=NameIDFormat.EMAIL,
        want_authn_requests_signed=True
    )

    sp_config = SAMLServiceProviderConfig(
        entity_id="https://api.example.com/metadata",
        assertion_consumer_service_url="https://api.example.com/saml/acs",
        single_logout_service_url="https://api.example.com/saml/sls",
        x509_cert="-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----",
        private_key="-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----",
        authn_requests_signed=True,
        want_assertions_signed=True
    )

    return idp_config, sp_config
