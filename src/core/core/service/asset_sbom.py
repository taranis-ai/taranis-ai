"""Compare and apply prepared inventory snapshots independently of the upload UI."""

from collections import defaultdict

from models.sbom import SbomComparison, SbomCreateAsset, component_identity

from core.managers.db_manager import db
from core.model.asset import Asset, AssetCpe, AssetGroup
from core.model.asset_intelligence import AssetMatchRun, AssetTrigger
from core.model.asset_sbom import AssetSbomComponent, AssetSbomImport, AssetSbomUpload
from core.model.user import User
from core.service.asset_intelligence import generate_triggers, product_identity


class SbomImportError(ValueError):
    def __init__(self, public_message: str, status: int):
        super().__init__(public_message)
        self.public_message = public_message
        self.status = status


def owned_import(import_id: str, user: User, *, lock=False) -> AssetSbomImport:
    query = db.select(AssetSbomImport).filter_by(id=import_id, user_id=user.id, organization_id=user.organization.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record = db.session.scalar(query)
    if not record or (record.asset_id and Asset.get_for_api(record.asset_id, user.organization)[1] != 200):
        raise SbomImportError("SBOM preview unavailable. Upload the file again.", 404)
    if db.session.scalar(
        db.select(AssetSbomUpload.id).where(AssetSbomUpload.import_id == record.id, AssetSbomUpload.status != "READY").limit(1)
    ):
        raise SbomImportError("The SBOM preview is still being prepared.", 409)
    return record


def current_import(asset_id: str) -> AssetSbomImport | None:
    return db.session.scalar(db.select(AssetSbomImport).filter_by(asset_id=asset_id))


def compare_import(record: AssetSbomImport, asset: Asset) -> SbomComparison:
    previous = current_import(asset.id)
    before = {component_identity(c.inventory) for c in previous.components} if previous else set()
    after = {component_identity(c.inventory) for c in record.components}
    old_cves = {f.cve_id for f in previous.findings if f.cve_id} if previous else set()
    new_cves = {f.cve_id for f in record.findings if f.cve_id}
    old_findings = {(f.cve_id or f.identifier) for f in previous.findings} if previous else set()
    new_findings = {(f.cve_id or f.identifier) for f in record.findings}
    return SbomComparison(
        asset_id=asset.id,
        asset_name=asset.name,
        expected_sha256=previous.sha256 if previous else None,
        components_added=len(after - before),
        components_removed=len(before - after),
        findings_added=len(new_findings - old_findings),
        findings_removed=len(old_findings - new_findings),
        cves_added=len(new_cves - old_cves),
        cves_removed=len(old_cves - new_cves),
        clears_findings=bool(previous and previous.findings and not record.summary.get("vulnerabilities_supplied")),
    )


def _rule_key(trigger: AssetTrigger) -> str:
    return trigger.rule.key


def _rule_decision(trigger: AssetTrigger) -> tuple:
    return trigger.enabled, trigger.analyst_edited


def preserve_rules(previous: AssetSbomImport, incoming: AssetSbomImport) -> None:
    """Move exact-version rules; inherit unanimous package decisions for new versions."""
    old_components = {component_identity(c.inventory): c for c in previous.components}
    by_package: dict[tuple, list[AssetSbomComponent]] = defaultdict(list)
    for component in previous.components:
        by_package[product_identity(component.inventory)].append(component)
    rules: dict[str, list[AssetTrigger]] = defaultdict(list)
    for trigger in db.session.scalars(db.select(AssetTrigger).join(AssetSbomComponent).where(AssetSbomComponent.import_id == previous.id)):
        rules[trigger.component_id].append(trigger)
    for component in incoming.components:
        if old := old_components.get(component_identity(component.inventory)):
            for trigger in rules[old.id]:
                trigger.component = component
            component.inventory = {**component.inventory, "review_conflicts": old.inventory.get("review_conflicts", [])}
            continue
        siblings = by_package.get(product_identity(component.inventory), [])
        decisions: dict[str, list[AssetTrigger]] = defaultdict(list)
        for sibling in siblings:
            for trigger in rules[sibling.id]:
                decisions[_rule_key(trigger)].append(trigger)
        conflicts = []
        for key, candidates in decisions.items():
            original = candidates[0]
            unanimous = len(candidates) == len(siblings) and len({_rule_decision(t) for t in candidates}) == 1
            inherited = AssetTrigger(
                component.id,
                original.rule,
                enabled=original.enabled if unanimous else False,
            )
            inherited.analyst_edited = original.analyst_edited or not unanimous
            db.session.add(inherited)
            if not unanimous:
                conflicts.append(key)
        component.inventory = {**component.inventory, "review_conflicts": conflicts}
    db.session.flush()


def apply_import(
    import_id: str,
    user: User,
    *,
    create: SbomCreateAsset | None = None,
    asset_id: str | None = None,
    expected_sha256: str | None = None,
    enable_software_matching: bool = True,
    enable_cve_matching: bool = True,
) -> tuple[Asset, bool]:
    """Apply one snapshot atomically; callers schedule matching only after this commits."""
    with db.session.begin_nested():
        asset, changed = _apply_import(
            import_id,
            user,
            create=create,
            asset_id=asset_id,
            expected_sha256=expected_sha256,
            enable_software_matching=create.enable_software_matching if create else enable_software_matching,
            enable_cve_matching=create.enable_cve_matching if create else enable_cve_matching,
        )
    db.session.commit()
    return asset, changed


def _apply_import(
    import_id: str,
    user: User,
    *,
    create: SbomCreateAsset | None,
    asset_id: str | None,
    expected_sha256: str | None,
    enable_software_matching: bool,
    enable_cve_matching: bool,
) -> tuple[Asset, bool]:
    asset = None
    if asset_id:
        if Asset.get_for_api(asset_id, user.organization)[1] != 200:
            raise SbomImportError("Asset not found.", 404)
        # A write also serializes replacement on SQLite, where FOR UPDATE is ignored.
        db.session.execute(db.update(Asset).where(Asset.id == asset_id).values(name=Asset.name))
        asset = db.session.get(Asset, asset_id)
    record = owned_import(import_id, user, lock=True)
    if record.asset_id:
        if asset_id and record.asset_id != asset_id:
            raise SbomImportError("This import belongs to another asset. Upload a new export.", 409)
        existing = db.session.get(Asset, record.asset_id)
        assert existing is not None
        return existing, False
    previous = current_import(asset_id) if asset_id else None
    if asset_id and (previous.sha256 if previous else None) != expected_sha256:
        raise SbomImportError("The asset inventory changed. Review the update again before applying it.", 409)
    if asset is None:
        if not create or not create.name.strip():
            raise SbomImportError("Provide an asset name.", 400)
        group = AssetGroup.get(create.asset_group_id)
        if not group or not AssetGroup.access_allowed(user.organization, group.id):
            raise SbomImportError("Asset group unavailable.", 403)
        asset = Asset(name=create.name.strip(), serial="", description=create.description, group=group, tags=create.tags)
        db.session.add(asset)
        db.session.flush()
    claimed = db.session.scalar(
        db.update(AssetSbomImport)
        .where(AssetSbomImport.id == record.id, AssetSbomImport.confirmed.is_(None))
        .values(confirmed=record.utcnow())
        .returning(AssetSbomImport.id)
    )
    if not claimed:
        raise SbomImportError("This import has already been applied. Reload the asset.", 409)
    old_projection = {cpe for c in previous.components for cpe in c.inventory["cpes"]} if previous else set()
    new_projection = {cpe for c in record.components for cpe in c.inventory["cpes"]}
    manual_cpes = {c.value for c in asset.asset_cpes} - old_projection
    desired_cpes = manual_cpes | new_projection
    asset.asset_cpes = [c for c in asset.asset_cpes if c.value in desired_cpes]
    retained_cpes = {c.value for c in asset.asset_cpes}
    asset.asset_cpes.extend(AssetCpe(cpe) for cpe in sorted(desired_cpes - retained_cpes))
    # Seed new CVEs before preserve_rules restores decisions for existing IDs.
    for finding in record.findings:
        if finding.cve_id:
            finding.matching_enabled = enable_cve_matching
    if previous:
        if previous.organization_id == record.organization_id:
            preserve_rules(previous, record)
        old_decisions = {finding.cve_id: finding.matching_enabled for finding in previous.findings if finding.cve_id}
        for finding in record.findings:
            if finding.cve_id in old_decisions:
                finding.matching_enabled = old_decisions[finding.cve_id]
        previous.asset_id = None
        db.session.flush()
        db.session.delete(previous)
    record.asset_id = asset.id
    db.session.flush()
    generate_triggers(asset.id, enable_software_matching=enable_software_matching)
    db.session.execute(
        db.update(AssetMatchRun)
        .where(AssetMatchRun.asset_id == asset.id, AssetMatchRun.status.in_(("QUEUED", "RUNNING")))
        .values(status="SUPERSEDED")
    )
    asset.update_vulnerabilities()
    return asset, True
