"""Standalone physical-context exchange, with no Rosetta dependency.

This candidate JSON profile uses explicit decimal strings. Its native digest is
not a Rosetta CID and does not assert RFC 8785 compatibility or source truth.
"""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

VERSION = "0.5.0"
ROLES = frozenset({"reported-measurement", "human-report", "inferred", "predicted", "simulated", "synthesized"})
GENERATED = frozenset({"predicted", "simulated", "synthesized"})
REQUIRED = frozenset({"schemaVersion", "recordId", "entity", "predicate", "role", "eventTime", "knownAt", "spatial", "quality", "sources", "derivation", "rights", "lifecycle", "origin"})

class ExchangeError(ValueError):
    """A named invariant of the standalone candidate was violated."""

def strict_loads(raw: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ExchangeError(f"Duplicate JSON member: {key}")
            result[key] = value
        return result
    def constant(value: str) -> None:
        raise ExchangeError(f"Nonfinite JSON constant: {value}")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        # The source may contain ordinary floats, but never overflow to infinity.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        return value
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, ExchangeError):
            raise
        raise ExchangeError("Input is not strict finite UTF-8 JSON") from exc

def instant(text: str) -> datetime:
    if not isinstance(text, str) or 'T' not in text:
        raise ExchangeError("Time must be a timezone-qualified ISO timestamp")
    try:
        result = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ExchangeError("Malformed timestamp") from exc
    if result.tzinfo is None:
        raise ExchangeError("Naive time is not an exchange time basis")
    return result.astimezone(timezone.utc)

def _quantity(text: Any) -> Decimal:
    if not isinstance(text, str):
        raise ExchangeError("Native quantities require explicit decimal strings")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ExchangeError("Invalid decimal quantity") from exc
    if not result.is_finite():
        raise ExchangeError("Quantity is not finite")
    return result

def _refs(values: Any, name: str, *, nonempty: bool = False) -> None:
    if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
        raise ExchangeError(f"{name} must be a list of nonempty references")
    if len(values) != len(set(values)) or (nonempty and not values):
        raise ExchangeError(f"{name} requires unique references")

def validate(record: dict) -> dict:
    if not isinstance(record, dict) or set(record) != REQUIRED:
        raise ExchangeError("Record fields differ from the bounded native profile")
    if record['schemaVersion'] != VERSION or record['role'] not in ROLES:
        raise ExchangeError("Unsupported profile version or evidence role")
    for field in ('recordId', 'entity', 'predicate', 'origin'):
        if not isinstance(record[field], str) or not record[field]:
            raise ExchangeError(f"Missing {field}")
    time = record['eventTime']
    if set(time) != {'start', 'end', 'basis'} or time['basis'] != 'UTC':
        raise ExchangeError("This time profile requires start/end and UTC")
    start, known = instant(time['start']), instant(record['knownAt'])
    end = instant(time['end']) if time['end'] is not None else start
    if end < start:
        raise ExchangeError("Observation interval is reversed")
    if record['role'] in {'reported-measurement', 'human-report'} and end > known:
        raise ExchangeError("A received observation cannot end after receipt")
    spatial = record['spatial']
    if set(spatial) != {'frame', 'units', 'position', 'orientation', 'transformRefs'}:
        raise ExchangeError("Incomplete spatial interpretation contract")
    if not spatial['frame'] or not isinstance(spatial['position'], list) or len(spatial['position']) not in (2, 3):
        raise ExchangeError("Position needs a named frame and two or three coordinates")
    if len(spatial['units']) != len(spatial['position']):
        raise ExchangeError("Every coordinate needs its own unit")
    numbers = [_quantity(x) for x in spatial['position']]
    if spatial['frame'] == 'OGC:CRS84':
        if spatial['units'][:2] != ['deg', 'deg'] or (len(numbers) == 3 and spatial['units'][2] != 'm'):
            raise ExchangeError("CRS84 requires longitude/latitude degrees and optional metre height")
        if not (-180 <= numbers[0] <= 180 and -90 <= numbers[1] <= 90):
            raise ExchangeError("Longitude or latitude is outside its range")
    elif any(unit != 'm' for unit in spatial['units']):
        raise ExchangeError("This Cartesian profile uses metres")
    _refs(spatial['transformRefs'], 'transformRefs')
    orientation = spatial['orientation']
    if orientation is not None:
        if set(orientation) != {'x', 'y', 'z', 'w'}:
            raise ExchangeError("Quaternion components are x/y/z/w")
        norm = sum(_quantity(x) ** 2 for x in orientation.values())
        if abs(norm - 1) > Decimal('0.000001'):
            raise ExchangeError("Quaternion is not unit length within the declared tolerance")
    quality = record['quality']
    if not isinstance(quality, dict) or quality.get('kind') not in {'unknown', 'bound', 'native-reference'}:
        raise ExchangeError("Quality must preserve its declared interpretation")
    if quality['kind'] == 'bound':
        if _quantity(quality.get('value')) < 0 or quality.get('unit') != 'm':
            raise ExchangeError("Position error bound must be nonnegative metres")
        if quality.get('interpretation') != 'declared-bound-not-calibrated':
            raise ExchangeError("A bound is not a calibrated probability")
    _refs(record['sources'], 'sources', nonempty=True)
    derivation = record['derivation']
    if set(derivation) != {'parents', 'method', 'branch', 'counterfactual'} or not derivation['method'] or not derivation['branch']:
        raise ExchangeError("Derivation requires method, branch and counterfactual state")
    _refs(derivation['parents'], 'parents')
    if type(derivation['counterfactual']) is not bool:
        raise ExchangeError("Counterfactual marker must be boolean")
    if record['role'] == 'reported-measurement' and derivation['counterfactual']:
        raise ExchangeError("Counterfactual output cannot be a reported measurement")
    rights = record['rights']
    if set(rights) != {'purposes', 'expiresAt', 'prohibitedInferences'}:
        raise ExchangeError("Rights require purposes, expiry and prohibited inferences")
    _refs(rights['purposes'], 'purposes', nonempty=True)
    _refs(rights['prohibitedInferences'], 'prohibitedInferences')
    if rights['expiresAt'] is not None and instant(rights['expiresAt']) <= known:
        raise ExchangeError("An already-expired grant cannot admit this record")
    life = record['lifecycle']
    if set(life) != {'operation', 'target', 'validUntil'} or life['operation'] not in {'assert', 'supersede', 'retract'}:
        raise ExchangeError("Unknown lifecycle operation")
    if (life['operation'] == 'assert') != (life['target'] is None):
        raise ExchangeError("Revision operations require a target; assertion does not")
    if life['validUntil'] is not None and instant(life['validUntil']) <= start:
        raise ExchangeError("Validity interval must be nonempty")
    strict_loads(json.dumps(record, ensure_ascii=False, allow_nan=False))
    return copy.deepcopy(record)

def native_digest(record: dict) -> str:
    checked = validate(record)
    encoded = json.dumps(checked, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return 'indranet-json-sha256:' + hashlib.sha256(encoded.encode()).hexdigest()

class Ledger:
    """In-memory, single-process demonstrator, not an authentication system."""
    def __init__(self) -> None:
        self._records: dict[str, dict] = {}
        self._digest: dict[str, str] = {}

    def admit(self, record: dict) -> str:
        record = validate(record)
        key = record['recordId']; digest = native_digest(record)
        if key in self._records:
            if self._digest[key] != digest:
                raise ExchangeError("A stable record identifier cannot name different immutable bytes")
            return digest
        parents = self.closure(record['derivation']['parents'])
        for parent in parents:
            if not set(record['rights']['purposes']).issubset(parent['rights']['purposes']):
                raise ExchangeError("Derived purpose exceeds transitive evidence grant")
            expiry = parent['rights']['expiresAt']
            if expiry and (record['rights']['expiresAt'] is None or instant(record['rights']['expiresAt']) > instant(expiry)):
                raise ExchangeError("Derived expiry exceeds evidence retention grant")
            if not set(parent['rights']['prohibitedInferences']).issubset(record['rights']['prohibitedInferences']):
                raise ExchangeError("Derived record drops an inherited prohibited inference")
            if record['role'] == 'reported-measurement' and parent['role'] in GENERATED:
                raise ExchangeError("Generated ancestry cannot be relabeled measured")
            if record['derivation']['branch'] == 'historical' and parent['derivation']['counterfactual']:
                raise ExchangeError("Counterfactual ancestry cannot become historical")
        life = record['lifecycle']
        if life['target'] is not None:
            if life['target'] not in self._records:
                raise ExchangeError("Revision target is unresolved")
            if life['target'] not in record['derivation']['parents']:
                raise ExchangeError('Revision target must be included in provenance parents')
            prior = self._records[life['target']]
            if any(prior[k] != record[k] for k in ('entity', 'predicate')):
                raise ExchangeError("Revision cannot change subject or predicate")
            if instant(prior['knownAt']) > instant(record['knownAt']):
                raise ExchangeError("Revision predates the target knowledge time")
        self._records[key], self._digest[key] = record, digest
        return digest

    def get(self, record_id: str) -> dict:
        if record_id not in self._records:
            raise ExchangeError(f"Unresolved record reference: {record_id}")
        return copy.deepcopy(self._records[record_id])

    def closure(self, refs: Iterable[str]) -> list[dict]:
        found: dict[str, dict] = {}; active: set[str] = set()
        def visit(ref: str) -> None:
            if ref in active:
                raise ExchangeError("Cyclic derivation")
            if ref in found:
                return
            active.add(ref); row = self.get(ref)
            for parent in row['derivation']['parents']:
                visit(parent)
            active.remove(ref); found[ref] = row
        for ref in refs:
            visit(ref)
        return list(found.values())

    def view(self, *, purpose: str, event_at: str, known_at: str, max_age_seconds: int = 2) -> dict:
        if not purpose or type(max_age_seconds) is not int or max_age_seconds < 0:
            raise ExchangeError("Purpose and nonnegative integer freshness budget are required")
        event, knowledge = instant(event_at), instant(known_at)
        eligible = [r for r in self._records.values() if instant(r['knownAt']) <= knowledge and instant(r['eventTime']['end'] or r['eventTime']['start']) <= event]
        retired = {r['lifecycle']['target'] for r in eligible if r['lifecycle']['target']}
        selected = []; omitted = 0
        for row in eligible:
            rights, life = row['rights'], row['lifecycle']
            if row['recordId'] in retired or life['operation'] == 'retract':
                continue
            if purpose not in rights['purposes'] or (rights['expiresAt'] and knowledge >= instant(rights['expiresAt'])):
                omitted += 1; continue
            if life['validUntil'] and event >= instant(life['validUntil']):
                continue
            # Emit state and source references, not the private source bytes.
            selected.append({'recordId': row['recordId'], 'entity': row['entity'], 'predicate': row['predicate'],
                'role': row['role'], 'spatial': copy.deepcopy(row['spatial']), 'quality': copy.deepcopy(row['quality']),
                'eventTime': copy.deepcopy(row['eventTime']), 'sources': list(row['sources']),
                'counterfactual': row['derivation']['counterfactual'], 'branch': row['derivation']['branch'],
                'prohibitedInferences': list(rights['prohibitedInferences']),
                'stale': (event - instant(row['eventTime']['end'] or row['eventTime']['start'])).total_seconds() > max_age_seconds})
        return {'purpose': purpose, 'states': selected, 'omitted': omitted, 'physicalActuationAuthority': False,
                'conflictPolicy': 'retain candidates; no automatic reconciliation or trust ranking'}
